import contextlib
import uuid

from django.db import models
import firebase_admin
import django.dispatch.dispatcher

import django.core.exceptions
from firebase_admin import messaging
import logging

logger = logging.getLogger(__name__)

status_choices = [
    ('ERROR', 'error'),
    ('SUCCESS', 'success'),
    ('INFO', 'info')
]

topic = 'notifications'

credentials = firebase_admin.credentials.Certificate(cert='./cert.json')
application = firebase_admin.initialize_app(credential=credentials)

UserCreated = django.dispatch.dispatcher.Signal()
UserDeleted = django.dispatch.dispatcher.Signal()

NotificationCreated = django.dispatch.dispatcher.Signal()


@django.dispatch.dispatcher.receiver(NotificationCreated)
def notification_created(notification_payload: dict, identifier=None, **kwargs):
    try:
        if not identifier in notification_payload.values():
            notification_payload['identifier'] = identifier
        Notification.objects.create(**notification_payload)
    except(django.db.utils.IntegrityError, django.db.utils.ProgrammingError, ) as exception:
        logger.debug('COULD NOT CREATE NOTIFICATION. ERROR OCCURRED %s' % exception)



class NotificationTransactionTriggerListener(object):
    """
    / * tracks incoming transaction into notification database, by listening for "triggers". In case,
    // * notification sends. There is no exact answer has it been delivered. So, that class
    """

    def __init__(self):
        self.creation_event = 'notification_created'
        self.deletion_event = 'notification_deleted'

    async def __call__(self, *args, **kwargs):
        """
        / * Asynchronously connects to postgresql database and executes sql query.
        """
        try:
            with self.listen_for_transaction() as connection:
                sql = self.get_sql_initial_command()
                connection.cursor().execute(sql)

                logger.debug('Initial SQL Code executed. Running Listeners.')
                await self.listen_for_delete_transaction()
                await self.listen_for_create_transaction()

        except(psycopg2.errors.CursorError, NotImplementedError) as exception:
            logger.error('Some Issues Occurred '
            'while executing SQL File %s' % exception)
            raise NotImplementedError()


    @contextlib.asynccontextmanager
    async def connect_to_db(self):
        import psycopg2
        try:
            db_credentials = getattr(settings, 'DATABASE_CREDENTIALS')
            yield psycopg2.connect(**db_credentials)
        except(psycopg2.errors.CursorError,) as exception:
            raise exception

    def get_sql_initial_command(self):
        """
        / * Creates two triggers for create/delete
        operations in "notifications" table. Of Firebase Db.
        """
        return """
        CREATE OR REPLACE FUNCTION notification_created_signal()
        RETURNS TRIGGER 
        LANGUAGE PLPGSQL
        AS $$
        DECLARE 
            channel notification_created := TG_ARGV[0];
        BEGIN 
            PERFORM 
                with payload(msg_id, rev, favs) as (
                    SELECT * FROM %s WHERE id=msg_id
                )
                SELECT pg_notify(channel, raw_to_json(payload)::notification_created)
                FROM payload
            RETURN NULL;
        END;
        $$
    
        CREATE TRIGGER notification_created 
        AFTER INSERT ON TABLE %s 
        EXECUTE PROCEDURE notification_created_signal()
        
        commit;
        """ % (getattr(models, 'notification_model'),
        getattr(models, 'notification_model'))


    async def listen_for_create_transaction(self):
        import psycopg2.errors
        try:
            with self.connect_to_db() as connection:
                connection.cursor().execute('LISTEN %s' % self.creation_event)
                Notification.objects.bulk_create([Notification(
                **notify.payload) for notify in connection.notifies])

        except(psycopg2.OperationalError, psycopg2.InternalError, psycopg2.DatabaseError) as exception:
            logger.error('EXCEPTION HAS OCCURRED WHILE RUNNING LISTENER: %s' % exception)
            raise NotImplementedError


    async def listen_for_delete_transaction(self):
        """
        / * This method is listening for triggers that happened
        """
        import psycopg2
        try:
            with self.connect_to_db() as connection:
                connection.cursor().execute('LISTEN %s' % self.deletion_event)

            for notif in connection.notifies:
                notification = models.Notification.objects.get(id=notif.payload.get('id'))
                notification.delete()
                logger.debug('notification with ID: %s has been deleted' % notif.payload.get('id'))

        except(psycopg2.errors.CursorError) as exception:
            logger.error('EXCEPTION HAS OCCURRED WHILE RUNNING LISTENER: %s' % exception)
            raise NotImplementedError


@django.dispatch.dispatcher.receiver(UserCreated)
def create_firebase_customer(customer, **kwargs):
    from firebase_admin import _user_identifier, auth
    firebase_customer = auth.create_user(display_name=customer.username,
    email=customer.email, app=application)
    customer.identifier = firebase_customer.uid
    customer.save(using=getattr(settings, 'DATABASES').keys()[0])


@django.dispatch.dispatcher.receiver(UserDeleted)
def delete_firebase_customer(customer_id, **kwargs):
    from firebase_admin import auth
    try:
        customer = models.Customer.objects.get(id=customer_id)
        auth.delete_user(uid=customer.identifier)
    except(django.core.exceptions.ObjectDoesNotExist,):
        raise NotImplementedError


class Notification(models.Model):

    objects = models.Manager()
    message = models.CharField(verbose_name='Message', max_length=100)
    status = models.CharField(choices=status_choices, max_length=10, default='success'.upper())
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.message


class CustomerQueryset(models.QuerySet):
    """
    / * Represents Customer Manager Class.
    """

    def create(self, **kwargs):
        try:
            user = self.model(**kwargs)
            user.save(using=self._db)

            messaging.subscribe_to_topic(tokens=[customer_token],
            topic=getattr(models, 'topic'), app=getattr(models, 'app'))
            UserCreated.send(sender=self, customer=user)
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

    username = models.CharField(verbose_name='Username', max_length=100, unique=True, editable=False)
    email = models.EmailField(verbose_name='Email', validators=[validators.EmailValidator,], editable=False, null=False)
    notify_token = models.CharField(verbose_name='Notify Token', max_length=100, null=False, editable=False)
    notifications = models.ForeignKey(Notification,
    on_delete=models.CASCADE, related_name='owner', null=True)
    created_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.username

    def delete(self, using=None, keep_parents=False):
        UserDeleted.send(sender=self, customer_id=self.id)
        return super().delete(using=using, keep_parents=keep_parents)




