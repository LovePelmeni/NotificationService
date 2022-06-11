import contextlib
import uuid

from django.db import models
import firebase_admin
import django.dispatch.dispatcher

import django.core.exceptions
from firebase_admin import messaging
import logging
from django.utils.translation import gettext_lazy as _
from django.db import transaction
logger = logging.getLogger(__name__)

status_choices = [
    ('ERROR', 'error'),
    ('SUCCESS', 'success'),
    ('INFO', 'info')
]

topic = 'notifications'
from django.conf import settings

credentials = firebase_admin.credentials.Certificate(cert=getattr(settings, 'CERTIFICATE_ABSOLUTE_PATH'))
application = firebase_admin.initialize_app(credential=credentials,
options={'databaseURL': getattr(settings, 'FIREBASE_DATABASE_URL')})


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


# class NotificationTransactionTriggerListener(object):
#     """
#     / * tracks incoming transaction into notification database, by listening for "triggers". In case,
#     // * notification sends. There is no exact answer has it been delivered. So, that class
#     """
#
#     def __init__(self):
#         self.creation_event = 'notification_created' # connects to database
#
#     async def __call__(self, *args, **kwargs):
#         """
#         / * Asynchronously connects to postgresql database and executes sql query.
#         """
#         try:
#             with self.listen_for_transaction() as connection:
#                 sql = self.get_sql_initial_command()
#                 connection.cursor().execute(sql)
#
#                 logger.debug('Initial SQL Code executed. Running Listeners.')
#                 await self.listen_for_delete_transaction()
#                 await self.listen_for_create_transaction()
#
#         except(psycopg2.errors.CursorError, NotImplementedError) as exception:
#             logger.error('Some Issues Occurred '
#             'while executing SQL File %s' % exception)
#             raise NotImplementedError()
#
#
#     @contextlib.asynccontextmanager
#     async def connect_to_db(self):
#         import psycopg2
#         try:
#             db_credentials = getattr(settings, 'DATABASE_CREDENTIALS')
#             yield psycopg2.connect(**db_credentials)
#         except(psycopg2.errors.CursorError,) as exception:
#             raise exception
#
#     def get_sql_initial_command(self):
#         """
#         / * Creates two triggers for create/delete
#         operations in "notifications" table. Of Firebase Db.
#         """
#         return """
#         CREATE OR REPLACE FUNCTION notification_created_signal()
#         RETURNS TRIGGER
#         LANGUAGE PLPGSQL
#         AS $$
#         DECLARE
#             channel notification_created := TG_ARGV[0];
#         BEGIN
#             PERFORM
#                 with payload(msg_id, rev, favs) as (
#                     SELECT * FROM %s WHERE id=msg_id
#                 )
#                 SELECT pg_notify(channel, raw_to_json(payload)::notification_created)
#                 FROM payload
#             RETURN NULL;
#         END;
#         $$
#
#         CREATE TRIGGER %s
#         AFTER INSERT ON TABLE %s
#         EXECUTE PROCEDURE notification_created_signal()
#
#         commit;
#         """ % (getattr(models, 'notification_model'), self.creation_event,
#         getattr(models, 'notification_model'))
#
#
#     async def listen_for_create_transaction(self):
#         import psycopg2.errors
#         try:
#             with self.connect_to_db() as connection:
#                 connection.cursor().execute('LISTEN %s' % self.creation_event)
#                 Notification.objects.bulk_create([Notification(
#                 **notify.payload) for notify in connection.notifies])
#
#         except(psycopg2.OperationalError, psycopg2.InternalError, psycopg2.DatabaseError) as exception:
#             logger.error('EXCEPTION HAS OCCURRED WHILE RUNNING LISTENER: %s' % exception)
#             raise NotImplementedError
#
#
#     async def listen_for_delete_transaction(self):
#         """
#         / * This method is listening for triggers that happened
#         """
#         import psycopg2
#         try:
#             with self.connect_to_db() as connection:
#                 connection.cursor().execute('LISTEN %s' % self.deletion_event)
#
#             for notif in connection.notifies:
#                 notification = models.Notification.objects.get(id=notif.payload.get('id'))
#                 notification.delete()
#                 logger.debug('notification with ID: %s has been deleted' % notif.payload.get('id'))
#
#         except(psycopg2.errors.CursorError) as exception:
#             logger.error('EXCEPTION HAS OCCURRED WHILE RUNNING LISTENER: %s' % exception)
#             raise NotImplementedError


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
        transaction.rollback(using='default')


@django.dispatch.dispatcher.receiver(UserDeleted)
def delete_firebase_customer(customer_id, **kwargs):
    from firebase_admin import auth
    try:
        customer = Customer.objects.get(id=customer_id)
        auth.delete_user(uid=customer.notify_token)
    except(django.core.exceptions.ObjectDoesNotExist,):
        raise NotImplementedError


class Notification(models.Model):

    objects = models.Manager()
    message = models.CharField(verbose_name='Message', max_length=100)

    identifier = models.CharField(verbose_name='Notification Identifier', max_length=100, null=False)
    status = models.CharField(choices=status_choices, max_length=10, default='success'.upper())

    created_at = models.DateTimeField(auto_now_add=True)
    receiver = models.CharField(verbose_name='Receiver FCM Token', max_length=100)

    def __str__(self):
        return self.message


class CustomerQueryset(models.QuerySet):
    """
    / * Represents Customer Manager Class.
    """

    def create(self, **kwargs):
        try:
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

    username = models.CharField(verbose_name='Username', max_length=100, unique=True)
    email = models.EmailField(verbose_name='Email', validators=[validators.EmailValidator,], editable=False, null=False)
    notify_token = models.CharField(verbose_name='Notify Token', max_length=1000, null=False, editable=True)
    notifications = models.ForeignKey(Notification,
    on_delete=models.CASCADE, related_name='owner', null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))


    def __str__(self):
        return self.username

    def delete(self, using=None, keep_parents=False):
        UserDeleted.send(sender=self, customer_id=self.id)
        return super().delete(using=using, keep_parents=keep_parents)



