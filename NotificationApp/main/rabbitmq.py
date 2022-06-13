import pika.exceptions
import firebase_admin.auth, typing
from django.conf import settings
from . import models


class RabbitMQConnection(object):

    @classmethod
    def connect_to_server(cls):
        """/ * Connects to Rabbitmq Server via credentials specified in the settings.py"""
        yield pika.BlockingConnection(parameters=
        pika.ConnectionParameters(host=getattr(settings, 'RABBITMQ_HOST'),
        port=getattr(settings, 'RABBITMQ_PORT'), heartbeat=10,
        credentials=pika.PlainCredentials(
        username=getattr(settings,'RABBITMQ_USER'),
        password=getattr(settings,'RABBITMQ_PASSWORD')), virtual_host=settings.RABBITMQ_VHOST)).channel()



class CustomerEventMessageHandler(object):
    """
    / * Handles Event messages related to customer.
    // * Has two methods for failure and request "messages".
    """

    @classmethod
    def handle_customer_message(cls, queue, method, properties, body):
        """Handles success messages."""
        try:
            body = json.loads(body).decode('utf-8')
            if properties.headers.get('METHOD') == 'POST':
                try:
                    models.Customer.objects.using(settings.MAIN_DATABASE).create(**body)
                except(NotImplementedError, firebase_admin._auth_utils.FirebaseError,):
                    raise NotImplementedError

            if properties.headers.get('METHOD') == 'DELETE':
                try:
                    customer = models.Customer.objects.using(
                    settings.MAIN_DATABASE).get(id=body.get('customer_id'))
                    customer.delete()
                except(django.core.exceptions.ObjectDoesNotExist, django.db.utils.IntegrityError,):
                    raise NotImplementedError

        except(NotImplementedError):
            raise NotImplementedError

    @classmethod
    def handle_customer_failure_message(cls, queue, method, properties, body):
            """Handles success messages """
            try:
                body = json.loads(body).decode('utf-8')

                if properties.headers.get('METHOD') == 'POST':
                    try:
                        customer = models.Customer.objects.get(**body)
                        customer.delete()
                    except(NotImplementedError, firebase_admin._auth_utils.FirebaseError,):
                        raise NotImplementedError

                if properties.headers.get('METHOD') == 'DELETE':
                    try:
                        customer = models.Customer.objects.using(
                        settings.BACKUP_DATABASE).get(id=body.get('customer_id'))
                        models.Customer.objects.using(settings.MAIN_DATABASE).create(
                        username=customer.username, email=customer.email, notify_token=customer.notify_token)

                    except(django.core.exceptions.ObjectDoesNotExist,
                    django.db.utils.IntegrityError, AttributeError):
                        raise NotImplementedError

            except(NotImplementedError):
                raise NotImplementedError


class CustomerRabbitMQMessageHandler(object, CustomerEventMessageHandler):

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

    __customer_queue__ = "customer_queue" # queues
    __customer_failure_queue__ = "customer_queue"

    __customer_exchange__ = "customer_exchange" # exchanges
    __customer_failure_exchange__ = "customer_failure_exchange"

    @classmethod
    def publish_customer_failure_event(cls, queue, failure_exchange, body: typing.Union[dict, str]):
        """
        / * Publish failure event, suppose other services will react and make a rollback.
        """
        with cls.connect_to_server() as connection:

            connection.basic_publish(exchange=failure_exchange,
            queue=queue, body=json.dumps(body))

    @classmethod
    def listen_customer_event(cls, queue, method, properties):
        """/ * Connects to "Subscription" and "Customer" queues. via "Headers" Exchange"""

        with cls.connect_to_server() as connection:

            connection.basic_consume(queue=cls.__customer_queue__,
            on_message_callback=cls.handle_customer_message)
            asgiref.sync.sync_to_async(connection.start_consuming)

            connection.basic_consume(queue=cls.__customer_failure_queue__,
            on_message_callback=cls.handle_customer_failure_message)
            asgiref.sync.sync_to_async(connection.start_consuming)

