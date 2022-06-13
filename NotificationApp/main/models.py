import contextlib
import uuid

from django.db import models
import firebase_admin
import django.dispatch.dispatcher

import django.core.exceptions
from firebase_admin import messaging
import logging
from django.utils.translation import gettext_lazy as _
from . import certificate, exceptions
from django.db import transaction

logger = logging.getLogger(__name__)

status_choices = [
    ('ERROR', 'error'),
    ('SUCCESS', 'success'),
    ('INFO', 'info')
]

topic = 'notifications'
from django.conf import settings

credentials = firebase_admin.credentials.Certificate(cert=getattr(certificate, 'CERTIFICATE_CREDENTIALS'))
application = firebase_admin.initialize_app(credential=credentials)


class Notification(models.Model):

    objects = models.Manager()
    message = models.CharField(verbose_name=_('Message'), max_length=100)

    identifier = models.CharField(verbose_name=_('Notification Identifier'), max_length=100, null=False)
    status = models.CharField(verbose_name=_('Notification Status'),
    choices=status_choices, max_length=10, default='success'.upper())

    created_at = models.DateTimeField(auto_now_add=True)
    receiver = models.CharField(verbose_name=_('Receiver FCM Token'), max_length=100)

    def __str__(self):
        return self.message


class CustomerQueryset(models.QuerySet):
    """
    / * Represents Customer Manager Class.
    """

    def rollback_firebase_transaction(self, uid):
        import firebase_admin._auth_utils
        try:
            import firebase_admin.auth
            return firebase_admin.auth.delete_user(uid=uid, app=application)
        except(firebase_admin._auth_utils.UserNotFoundError,):
            logger.error('could not remove Customer Firebase Profile: uid = %s' % uid)


    @transaction.atomic
    def create(self, **kwargs):
        import jwt, firebase_admin.exceptions
        try:
            from firebase_admin import messaging
            from firebase_admin import auth
            import datetime

            customer = self.model(username=kwargs.get('username'), email=kwargs.get('email'))
            customer.notify_token = kwargs.get('notify_token')
            customer.save(using=settings.MAIN_DATABASE)
            customer.refresh_from_db(using=settings.MAIN_DATABASE)

            subscription = messaging.subscribe_to_topic(tokens=[customer.notify_token],
            topic='notifications', app=application)

            if not subscription.success_count and subscription.failure_count:

                logger.error('Failed To Subscribe on topic: Error: %s' %
                list('%s, %s' % (error.reason, error.index)
                for error in subscription._errors if hasattr(error, 'reason')))

                self.rollback_firebase_transaction(uid=customer.notify_token)
                raise exceptions.FCMSubscriptionError()

            return customer

        except(django.db.utils.IntegrityError, jwt.PyJWTError,) as exception:
            raise exception

        except(ValueError,) as exception:
            logger.error('exception: %s' % exception)
            raise exception

        except(exceptions.FCMSubscriptionError,) as exception:
            raise exception

        except(firebase_admin.exceptions.InvalidArgumentError) as exception:
            logger.debug('Invalid FCM Token has been obtained...')
            raise exception


class CustomerManager(django.db.models.manager.BaseManager.from_queryset(queryset_class=CustomerQueryset)):
    pass


from django.core import validators

class Customer(models.Model):

    objects = CustomerManager()

    username = models.CharField(verbose_name=_('Username'), max_length=100, unique=True)
    email = models.EmailField(verbose_name=_('Email'), validators=[validators.EmailValidator,], editable=False, null=False)
    notify_token = models.CharField(verbose_name=_('Notify Token'), max_length=128, null=False, editable=False)
    notifications = models.ForeignKey(Notification,
    on_delete=models.CASCADE, related_name='owner', null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))


    def __str__(self):
        return self.username

    def create_backup(self):
        Customer.objects.create(username=self.username,
        email=self.email, notify_token=self.notify_token, created_at=self.created_at)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        asgiref.sync.sync_to_async(self.create_backup)(self) # asynchronously making backup.
        return super().save(using=using, force_update=force_update,
        force_insert=force_insert, update_fields=update_fields)

    def delete(self, using=None, keep_parents=False, **kwargs):
        import firebase_admin._auth_utils
        try:
            from firebase_admin import auth
            messaging.unsubscribe_from_topic(tokens=[self.notify_token],
            topic=topic, app=getattr(models, 'app'))
            auth.delete_user(uid=self.notify_token)
            return super().delete(using=using, keep_parents=keep_parents)

        except(firebase_admin._auth_utils.UserNotFoundError,):
            raise NotImplementedError





