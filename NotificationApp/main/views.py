import contextlib

import firebase_admin.db._sseclient
from django.shortcuts import render
import django.http

from rest_framework import viewsets, views, generics, permissions
from django.views.decorators import csrf
from . import models, authentication, notification_api

import django.core.exceptions
from rest_framework import status, generics
import logging


logger = logging.getLogger(__name__)


class CustomerGenericAPIView(generics.GenericAPIView):

    queryset = models.Customer.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.UserAuthenticationClass,)

    def handle_exception(self, exc):

        if isinstance(exc, django.core.exceptions.ObjectDoesNotExist):
            return django.http.HttpResponseNotFound()

        if isinstance(exc, django.core.exceptions.PermissionDenied):
            return django.http.HttpResponse(status=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS)

        return django.http.HttpResponseServerError()

    @csrf.requires_csrf_token
    def post(self, request):
        serializer = serializers.CustomerSerializer(request.data)
        if serializers.is_valid(raise_exception=True):
            models.Customer.objects.create(
            **serializer.validated_data)

        logger.debug('new customer has been created.')
        return django.http.HttpResponse(status=status.HTTP_201_CREATED)

    @csrf.requires_csrf_token
    def put(self, request):
        customer = models.Customer.objects.get(id=request.query_params.get('customer_id'))
        serializer = serializers.CustomerUpdateSerializer(request.data)

        if serializers.is_valid(raise_exception=True):
            for element, value in serializer.validated_data.items():
                customer.__setattr__(element, value)

            customer.save()
        return django.http.HttpResponse(status=200)

    @csrf.requires_csrf_token
    def delete(self, request):
        try:
            logout(request)
            customer = models.Customer.objects.get(
            id=request.query_params.get('customer_id'))
            customer.delete()
            return django.http.HttpResponse(status=200)
        except(django.core.exceptions.ObjectDoesNotExist,
        django.db.utils.IntegrityError) as exception:
            raise exception


class NotificationViewSet(viewsets.ModelViewSet):

    def __init__(self):
        super(NotificationViewSet, self).__init__()

    def get_authenticators(self):
        from . import authentication
        return (authentication.UserAuthenticationClass(),)

    def check_permissions(self, request):
        if not 'Authorization' in request.META.keys():
            return django.core.exceptions.PermissionDenied()
        return self.get_authenticators()[0].authenticate(request=request)

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
        queryset = models.Notification.objects.annotate(recently_obtained=

        db_models.ExpressionWrapper(expression=db_models.lookups.LessThan(
        datetime.datetime.now().weekday - db_models.F('created_at'), 7),
        output_field=db_models.BooleanField()))

        return django.http.HttpResponse(status=status.HTTP_200_OK,
        content=json.dumps({'notifications': list(queryset.values())},
        cls=django.core.serializers.json.DjangoJSONEncoder))


    @decorators.action(methods=['post'], detail=False)
    def create(self, request, **kwargs):

        from . import notification_api
        notification = notification_api.NotificationRequest(

        request.data.get('notification_payload'), title=request.data.get('title'),
        to=notification_api.NotifyToken(request.query_params.get('customer_token')))

        notification.send_notification()
        return django.http.HttpResponse(status=status.HTTP_201_CREATED)











