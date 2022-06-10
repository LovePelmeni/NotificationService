from django.shortcuts import render
import django.http

from rest_framework import viewsets, views, generics, permissions
from django.views.decorators import csrf
from . import models, authentication, permissions

import django.core.exceptions
from rest_framework import status

import logging
logger = logging.getLogger(__name__)


class CustomerGenericAPIView(generics.GenericAPIView):

    queryset = models.Customer.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (authentication.UserAuthenticationClass,)

    @csrf.requires_csrf_token
    def post(self, request):
        serializer = serializers.CustomerSerializer(request.data)
        if serializers.is_valid(raise_exception=True):
            models.Customer.objects.create_user(**serializer.validated_data)

        logger.debug('new customer has been created.')
        return django.http.HttpResponse(status=status.HTTP_201_CREATED)

    @csrf.requires_csrf_token
    def put(self, request, **kwargs):
        pass

    @csrf.requires_csrf_token
    def delete(self, request):
        try:
            logout(request)
            request.user.delete()
            return django.http.HttpResponse(status=200)
        except(django.core.exceptions.ObjectDoesNotExist,
        django.db.utils.IntegrityError):
            pass

class NotificationViewSet(viewsets.ModelViewSet):

    def get_authenticators(self):
        from . import authentication
        return (authentication.UserAuthenticationClass,)

    def check_permissions(self, request):
        if not request.user.is_authenticated or not 'Authorization' in request.META:
            return django.core.exceptions.PermissionDenied()
        return self.get_authenticators()[0].authenticate(request=request)

    @decorators.action(methods=['post'], detail=False)
    def create(self, request, **kwargs):
        from . import notification_api
        notification = notification_api.NotificationRequest(
        request.data.get('notification_payload'), title=request.data.get('title'),
        to=notification_api.NotifyToken())

        if not request.user.notify_token:
            notification.subscribe_to_notifications(customer_token=request.user.notify_token)
        notification.send_notification()
        return django.http.HttpResponse(status=status.HTTP_201_CREATED)

    @decorators.action(methods=['delete'], detail=False)
    def delete(self, request):
        import firebase_admin.db
        if request.query_params.get('notification_identifier'):
            pass


    @decorators.action(methods=['put'], detail=False)
    def update(self, request, *args, **kwargs):
        pass

