import contextlib

from django.shortcuts import render
import django.http
from rest_framework import decorators

from rest_framework import viewsets, views, generics, permissions
from django.views.decorators import csrf
from . import models, authentication, notification_api, serializers

import django.core.exceptions
from rest_framework import status, generics
import logging

from django.db import transaction
logger = logging.getLogger(__name__)



class CustomerGenericAPIView(viewsets.ModelViewSet):

    queryset = models.Customer.objects.all()
    permission_classes = (permissions.AllowAny,)

    def handle_exception(self, exc):

        if isinstance(exc, django.core.exceptions.ObjectDoesNotExist):
            return django.http.HttpResponseNotFound()

        if isinstance(exc, django.core.exceptions.PermissionDenied):
            return django.http.HttpResponse(status=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS)

        if isinstance(exc, django.core.exceptions.ValidationError):
            return django.http.HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        # return django.http.HttpResponseServerError()
        raise exc


    @transaction.atomic
    @csrf.csrf_exempt
    @decorators.action(methods=['post'], detail=False)
    def create(self, request):
        try:
            serializer = serializers.CustomerSerializer(data=request.data, many=False)
            if serializer.is_valid(raise_exception=True):
                models.Customer.objects.create(
                **serializer.validated_data)

            logger.debug('new customer has been created.')
            return django.http.HttpResponse(status=status.HTTP_201_CREATED)

        except(django.core.exceptions.ValidationError,) as exception:
            raise exception

        except(django.db.utils.IntegrityError,):
            transaction.rollback()
            raise django.core.exceptions.ValidationError(message='Form is not valid.')

    @transaction.atomic
    @csrf.csrf_exempt
    @decorators.action(methods=['put'], detail=False)
    def update(self, request):
        try:
            customer = models.Customer.objects.get(id=request.query_params.get('customer_id'))
            serializer = serializers.CustomerUpdateSerializer(data=request.data, many=False)

            if serializer.is_valid(raise_exception=True):
                for element, value in serializer.validated_data.items():
                    customer.__setattr__(element, value)

                customer.save()
            return django.http.HttpResponse(status=200)
        except(django.db.utils.IntegrityError,
        django.core.exceptions.ObjectDoesNotExist,):
            transaction.rollback()
            raise django.core.exceptions.ValidationError(message='Error.')

    @transaction.atomic
    @csrf.csrf_exempt
    @decorators.action(methods=['delete'], detail=False)
    def destroy(self, request):
        try:
            customer = models.Customer.objects.get(
            id=request.query_params.get('customer_id'))
            customer.delete()
            return django.http.HttpResponse(status=200)
        except(django.core.exceptions.ObjectDoesNotExist,
        django.db.utils.IntegrityError):
            raise django.core.exceptions.ValidationError


class NotificationSingleViewSet(viewsets.ModelViewSet):

    queryset = models.Notification.objects.all()


    def handle_exception(self, exception):
        if isinstance(exception, django.core.exceptions.ObjectDoesNotExist):
            return django.http.HttpResponse(status=status.HTTP_404_NOT_FOUND)
        # return django.http.HttpResponseServerError()
        raise exception

    @decorators.action(methods=['get'], detail=True)
    def retrieve(self, request, *args, **kwargs):
        notification = models.Notification.objects.get(
        id=request.query_params.get('notification_id'))
        return django.http.HttpResponse(status=status.HTTP_200_OK,
        content={'notification': list(notification.values())})


    @decorators.action(methods=['get'], detail=False)
    def list(self, request, *args, **kwargs):

        from django.db import models as db_models
        import datetime
        import django.core.serializers.json

        queryset = self.get_queryset().annotate(
        obtained_days_ago='received %s ago' % db_models.F('created_at'))

        return django.http.HttpResponse(status=status.HTTP_200_OK,
        content=json.dumps({'notifications': list(queryset.values())},
        cls=django.core.serializers.json.DjangoJSONEncoder))


    @csrf.csrf_exempt
    @decorators.action(methods=['post'], detail=False)
    def create(self, request, **kwargs):

        from . import notification_api
        try:
            customer_receiver = models.Customer.objects.get(id=request.data.get('customer_id'))
            notification = notification_api.NotificationSingleRequest(

            body=request.data.get('notification_payload'), title=request.data.get('title'),
            to=notification_api.NotifyToken(customer_receiver.notify_token))

            notification.send_notification()
            return django.http.HttpResponse(status=status.HTTP_201_CREATED)
        except(django.core.exceptions.ObjectDoesNotExist,
        django.db.utils.IntegrityError,) as exception:
            raise exception


class NotificationMultiUserViewSet(viewsets.ModelViewSet):
    """
    / * Represents Controller for multiple-destination notifications
    """

    @decorators.action(methods=['post'], detail=False, description='Sends Single Notification for multiple users.')
    def create(self, request):
        receivers = [notification_api.NotifyToken(token) for token
        in json.loads(request.data.get('receivers').split(' '))]
        notification_payload = request.data.get('notification_payload')

        notification = notification_api.NotificationMultiRequest(receivers=receivers, body=notification_payload)
        notification.send_one_to_many_notification()
        return django.http.HttpResponse(status=status.HTTP_201_CREATED)
