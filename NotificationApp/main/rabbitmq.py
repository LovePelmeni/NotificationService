import contextlib

import pika.exceptions, asgiref.sync
import firebase_admin.auth, typing
from django.conf import settings

from . import models, exceptions
from retry import retry
import logging
import django.db.utils

logger = logging.getLogger(__name__)




def configure_rabbitmq_server():

    customer_queue = connection.queue_declare(queue='customer_queue', exclusive=False, durable=True)
    customer_failure_queue = connection.queue_declare(queue='customer_failure_queue', exclusive=False,  durable=True)
    subscription_queue = connection.queue_declare(queue='subscription_queue', exclusive=False,  durable=True)
    subscription_failure_queue = connection.queue_declare(
    queue='subscription_failure_queue', exclusive=False,  durable=True)

    connection.exchange_declare(exchange="customer_exchange", exchange_type="fanout")
    connection.exchange_declare(exchange='customer_failure_exchange', exchange_type="fanout")
    connection.exchange_declare(exchange='subscription_exchange', exchange_type="fanout")
    connection.exchange_declare(
    exchange='subscription_failure_exchange', exchange_type="fanout")

    connection.queue_bind(queue=customer_queue.method.queue, exchange="customer_exchange")
    connection.queue_bind(queue=customer_failure_queue.method.queue, exchange="customer_failure_exchange")
    connection.queue_bind(queue=subscription_queue.method.queue, exchange="subscription_exchange")
    connection.queue_bind(queue=subscription_failure_queue.method.queue, exchange="subscription_failure_exchange")

    logger.debug('Queues binded..')






class RabbitMQConnection(object):

    __nodes__: typing.ClassVar[typing.List[pika.URLParameters]] = [ # cluster nodes for rabbitmq server.


        pika.URLParameters("amqp://%s:%s@%s:%s/%s" % (settings.RABBITMQ_USER,
        settings.RABBITMQ_PASSWORD, settings.RABBITMQ_HOST, settings.RABBITMQ_PORT, settings.RABBITMQ_VHOST)),

        pika.URLParameters("amqp://%s:%s@%s:%s/%s" % (settings.RABBITMQ_USER,
        settings.RABBITMQ_PASSWORD, settings.RABBITMQ_NODE2_HOST,
        settings.RABBITMQ_NODE3_PORT, settings.RABBITMQ_VHOST)),

        pika.URLParameters("amqp://%s:%s@%s:%s/%s" % (settings.RABBITMQ_USER,
        settings.RABBITMQ_PASSWORD, settings.RABBITMQ_NODE3_HOST,
        settings.RABBITMQ_NODE3_PORT, settings.RABBITMQ_VHOST)),

    ]

    @classmethod
    @contextlib.contextmanager
    @retry(exceptions=(NotImplementedError, pika.exceptions.ChannelError, pika.exceptions.AMQPError,), delay=5)
    def connect_to_server(cls):
        """/ * Connects to Rabbitmq Server via credentials specified in the settings.py"""
        try:
            yield pika.BlockingConnection(cls.__nodes__).channel()
        except(pika.exceptions.AMQPError, pika.exceptions.ConnectionClosed, pika.exceptions.ChannelError,) as error:
            logger.critical('Exception while RabbitMQ Connection Process. %s' % error)
            raise exceptions.RabbitMQServerIsNotRunning()




class CustomerEventMessageHandler(object):
    """
    / * Handles Event messages related to customer.
    // * Has two methods for failure and request "messages".
    """

    @classmethod
    def handle_customer_message(cls, properties, body):
        """Handles success messages."""
        try:
            body = json.loads(body).decode('utf-8')
            if properties.headers.get('METHOD').upper() == 'POST':
                try:
                    models.Customer.objects.using(settings.MAIN_DATABASE).create(**body)
                except(NotImplementedError, firebase_admin._auth_utils.FirebaseError,
                django.db.utils.Error) as exception:
                    logger.info('FAILED TO CREATE USER. %s. SENDING FAILURE EVENT...' % exception)
                    raise NotImplementedError


            if properties.headers.get('METHOD').upper() == 'DELETE':
                try:
                    customer = models.Customer.objects.using(
                    settings.MAIN_DATABASE).get(id=body.get('customer_id'))
                    customer.delete()
                except(django.core.exceptions.ObjectDoesNotExist, django.db.utils.IntegrityError,) as exception:
                    logger.info('CUSTOMER RABBITMQ EXCEPTION. Reason: %s' % exception)
                    raise NotImplementedError

        except(NotImplementedError):
            raise NotImplementedError

    @classmethod
    def handle_customer_failure_message(cls, properties, body):
            """Handles success messages """
            try:
                body = json.loads(body).decode('utf-8')
                if properties.headers.get('METHOD').upper() == 'POST':
                    try:
                        customer = models.Customer.objects.get(**body)
                        customer.delete()
                    except(NotImplementedError, firebase_admin._auth_utils.FirebaseError,
                    django.db.utils.IntegrityError, django.core.exceptions.ObjectDoesNotExist,) as exception:

                        logger.info('FAILED TO ROLLBACK USER CREATION. %s' % exception)
                        raise NotImplementedError

                if properties.headers.get('METHOD').upper() == 'DELETE':
                    try:
                        customer = models.Customer.objects.using(
                        settings.BACKUP_DATABASE).get(id=body.get('customer_id'))
                        models.Customer.objects.using(settings.MAIN_DATABASE).create(
                        username=customer.username, email=customer.email, notify_token=customer.notify_token)

                    except(django.core.exceptions.ObjectDoesNotExist,
                    django.db.utils.IntegrityError, AttributeError) as exception:
                        logger.info('CUSTOMER RABBITMQ MESSAGE EXCEPTION. Reason: %s' % exception)
                        raise NotImplementedError

            except(NotImplementedError):
                raise NotImplementedError


class CustomerRabbitMQMessageHandler(RabbitMQConnection, CustomerEventMessageHandler):

    """
    / * Class Represents Handler for RabbitMQ messages related to customer in the current service.
    // * Use simple pika client connection as an implementation


    Attributes represent queues and exchange types for handling incoming messages.
    In the scenario of the whole project I decided to user exchanges with "" type.
    So the following distributed communication going to be the way:


    The main service sends request message to all services. If one of them fails,
     that service going to send request message with "failed" prefix, so the exchange is going to be "fanout" and
     all the services will receive them and will make a rollback.


     So I added a pair of ("success" and "failure") exchanges for the "key" models in the distributed system.

     Info about method/ GET/POST data and so on I'm going store in message "headers".

    """

    from collections.abc import Sequence

    __customer_queue__: typing.ClassVar[str] =  "customer_queue" # queues
    __customer_failure_queue__: typing.ClassVar[str] = "customer_failure_queue"

    __customer_exchange__ : typing.ClassVar[str] = "customer_exchange" # exchanges
    __customer_failure_exchange__ : typing.ClassVar[str] =  "customer_failure_exchange"
    __service_name__: typing.ClassVar[str] = 'NotificationService'


    def __new__(cls, *args, **kwargs):
        cls.listen_customer_event()

    @classmethod
    def listen_customer_event(cls):
        """/ * Connects to "Subscription" and "Customer" queues. via "Headers" Exchange"""

        with cls.connect_to_server() as connection:

                connection.basic_consume(queue=cls.__customer_queue__,
                on_message_callback=cls.handle_customer_queue_messages)
                asgiref.sync.sync_to_async(connection.start_consuming)

                connection.basic_consume(queue=cls.__customer_failure_queue__,
                on_message_callback=cls.handle_customer_failure_queue_messages)
                asgiref.sync.sync_to_async(connection.start_consuming)

    @classmethod
    def handle_customer_failure_queue_messages(cls, queue, method, properties, body):
        try:
            if properties.headers['sender'] in (cls.__service_name__,):
                pass
            else:
                cls.handle_customer_failure_message(properties, body)
                logger.debug('transaction has been rollback.')
        except(NotImplementedError,):
            logger.critical('ROLLBACK FAILED. ')

        except(KeyError,):
            logger.error('No "sender" header specified.')

    @classmethod
    def handle_customer_queue_messages(cls, queue, method, properties, body):
        try:
            cls.handle_customer_message(properties, body)
            logger.debug('new incoming message has been obtained..')
            properties.headers['sender'] = 'NotificationService'

        except(NotImplementedError,):
            cls.publish_customer_failure_event(body=body, properties=properties)
            logger.debug('published failure event, due to Exception.')

        except(KeyError,):
            logger.error('No "sender" header specified.')

    @classmethod
    def publish_customer_failure_event(cls, body: typing.Union[dict, str],
    properties: pika.BasicProperties):
        """
        / * Publish failure event, suppose other services will react and make a rollback.
        """
        with cls.connect_to_server() as connection:

            connection.basic_publish(exchange=cls.__customer_failure_exchange__,
            queue=cls.__customer_failure_queue__, body=json.dumps(body), properties=properties)


handler = CustomerRabbitMQMessageHandler()

