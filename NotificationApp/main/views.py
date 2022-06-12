import typing, pydantic

from django.shortcuts import render
import django.http
from rest_framework import decorators

from rest_framework import viewsets, views, generics, permissions
from django.views.decorators import csrf
from . import models, authentication, notification_api, serializers, exceptions

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

        return django.http.HttpResponseServerError()


    @transaction.atomic
    @csrf.csrf_exempt
    @decorators.action(methods=['post'], detail=False)
    def create(self, request):
        import rest_framework.exceptions
        try:
            serializer = serializers.CustomerSerializer(data=request.data, many=False)
            if serializer.is_valid(raise_exception=True):
                models.Customer.objects.create(
                **serializer.validated_data)

            logger.debug('new customer has been created.')
            return django.http.HttpResponse(status=status.HTTP_201_CREATED)

        except(django.core.exceptions.ValidationError,
        rest_framework.exceptions.ValidationError,) as exception:
            raise exception

        except(django.db.utils.IntegrityError,):
            raise django.core.exceptions.ValidationError(message='Form is not valid.')

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

        import firebase_admin.exceptions
        if isinstance(exception, django.core.exceptions.ObjectDoesNotExist):
            return django.http.HttpResponse(status=status.HTTP_404_NOT_FOUND)

        if issubclass(exception.__class__, firebase_admin.exceptions.FirebaseError):
            return django.http.HttpResponse(status=status.HTTP_424_FAILED_DEPENDENCY)

        return django.http.HttpResponseServerError()


    @decorators.action(methods=['get'], detail=True)
    def retrieve(self, request, *args, **kwargs):
        from django.db import models as db_models
        from . import models
        import json
        notification = list(models.Notification.objects.filter(
        id=request.query_params.get('notification_id')).values())
        return django.http.HttpResponse(status=status.HTTP_200_OK,
        content=json.dumps({'notification': notification},
        cls=django.core.serializers.json.DjangoJSONEncoder))


    @decorators.action(methods=['get'], detail=False)
    def list(self, request, *args, **kwargs):

        from django.db import models as db_models
        import datetime, json
        import django.core.serializers.json

        queryset = self.get_queryset().annotate(
        obtained_days_ago=db_models.Value('received %s ago' % db_models.F('created_at')))

        return django.http.HttpResponse(status=status.HTTP_200_OK,
        content=json.dumps({'notifications': list(queryset.values())},
        cls=django.core.serializers.json.DjangoJSONEncoder))


    @csrf.csrf_exempt
    @decorators.action(methods=['post'], detail=False)
    def create(self, request, **kwargs):
        from . import notification_api
        try:
            notification_data = serializers.NotificationSerializer(data=request.data, many=False)
            if notification_data.is_valid(raise_exception=True):
                customer_receiver = models.Customer.objects.get(

                id=notification_data.validated_data['customer_id']).notify_token
                del notification_data.validated_data['customer_id']

                notification = notification_api.NotificationSingleRequest(
                **notification_data.validated_data, to=notification_api.NotifyToken(token=customer_receiver))

                notification.send_notification()
                return django.http.HttpResponse(status=status.HTTP_201_CREATED)

        except(django.core.exceptions.ObjectDoesNotExist,
        django.db.utils.IntegrityError, exceptions.FCMSubscriptionError,) as exception:
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

