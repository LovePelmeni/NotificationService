import contextlib
import uuid

from django.db import models
import firebase_admin
import django.dispatch.dispatcher

import django.core.exceptions
from firebase_admin import messaging
import logging
from django.utils.translation import gettext_lazy as _
from . import certificate
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


from firebase_admin import firestore
database_client = firestore.client(app=application)

USER_DATABASE = database_client.collections(u'users', timeout=10)
NOTIFICATION_DATABASE = database_client.collections(u'notifications', timeout=10)

UserCreated = django.dispatch.dispatcher.Signal()
UserDeleted = django.dispatch.dispatcher.Signal()

NotificationCreated = django.dispatch.dispatcher.Signal()

@django.dispatch.dispatcher.receiver(NotificationCreated)
def notification_created(notification_payload: dict, **kwargs):
    try:
        Notification.objects.create(**notification_payload)
    except(django.db.utils.IntegrityError, django.db.utils.ProgrammingError, KeyError, AttributeError) as exception:
        logger.debug('COULD NOT CREATE NOTIFICATION. ERROR OCCURRED %s' % exception)
        raise NotImplementedError

@django.dispatch.dispatcher.receiver(UserCreated)
@transaction.atomic
def create_firebase_customer(customer, **kwargs):
    from firebase_admin import auth
    import datetime

    try:
        generated_uid = str(uuid.uuid4()) + '%s' % datetime.datetime.now()
        # / * generates unique identifier for
        # notification client based on user creation data.
        firebase_customer = auth.create_user(display_name=customer.username,
        email=customer.email, app=application, disabled=False, uid=generated_uid, email_verified=True)
        generated_token = auth.create_custom_token(uid=firebase_customer.uid, app=application)
        customer.notify_token = generated_token
        customer.save(using='default')

    except(firebase_admin._auth_utils.EmailAlreadyExistsError,):
        logger.debug('User with following email: %s already exists.' % customer.email)


@django.dispatch.dispatcher.receiver(UserDeleted)
def delete_firebase_customer(customer_id, **kwargs):
    from firebase_admin import auth, _auth_utils
    try:
        customer = Customer.objects.get(id=customer_id)
        auth.delete_user(uid=customer.notify_token)
    except(django.core.exceptions.ObjectDoesNotExist, _auth_utils.UserNotFound,):
        raise NotImplementedError


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

    def create(self, **kwargs):
        try:
            from firebase_admin import messaging
            user = self.model(username=kwargs.get('username'),
            email=kwargs.get('email'))
            UserCreated.send(sender=self, customer=user)

            user.save(using=self._db)
            user.refresh_from_db()

            messaging.subscribe_to_topic(tokens=[user.notify_token],
            topic=topic, app=application)
            return user
        except(django.db.utils.IntegrityError,) as exception:
            raise exception

    def delete(self, **kwargs):
        try:
            messaging.unsubscribe_from_topic(tokens=[kwargs.get('customer_token')],
            topic=topic, app=getattr(models, 'app'))
            return super().delete()
        except(django.db.utils.IntegrityError,
        django.core.exceptions.ObjectDoesNotExist) as exception:
            raise exception

class CustomerManager(django.db.models.manager.BaseManager.from_queryset(queryset_class=CustomerQueryset)):
    pass

from django.core import validators

class Customer(models.Model):

    objects = CustomerManager()

    username = models.CharField(verbose_name=_('Username'), max_length=100, unique=True)
    email = models.EmailField(verbose_name=_('Email'), validators=[validators.EmailValidator,], editable=False, null=False)
    notify_token = models.CharField(verbose_name=_('Notify Token'), max_length=1000, null=False, editable=True)
    notifications = models.ForeignKey(Notification,
    on_delete=models.CASCADE, related_name='owner', null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))


    def __str__(self):
        return self.username

    def delete(self, using=None, keep_parents=False, **kwargs):
        UserDeleted.send(sender=self, customer_id=self.id)
        return super().delete(using=using, keep_parents=keep_parents)



