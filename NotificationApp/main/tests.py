import typing
import unittest.mock

import firebase_admin, pytest
import firebase_admin.auth
import pika
from django.test import TestCase

from django import test
import parameterized.parameterized
import django.conf, logging

from rest_framework import status
from . import models
from django.conf import settings
from django.db.models import signals
from django.test import override_settings


client = test.Client()
logger = logging.getLogger(__name__)

class CustomerAPITestCase(TestCase):

    def setUp(self) -> None:
        import rest_framework.exceptions
        try:
            self.customer_data = {'username': 'dfr', 'email': 'nfl@gmail.com'}
            self.customer = models.Customer.objects.create(**self.customer_data)
            self.another_customer_data = {'username': 'Anser', "email": "anofs_il@gmail.com"}

        except(rest_framework.exceptions.ValidationError,):
            raise NotImplementedError()

    def test_create_customer(self):

        response = client.post('http://localhost:8000/create/customer/',
        data=self.another_customer_data, timeout=10)
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertGreater(len(models.Customer.objects.all()), 1)

    def tearDown(self):
        try:
            models.Customer.objects.get(id=self.customer.id).delete()
        except(firebase_admin._auth_utils.UserNotFoundError,):
            pass
        finally:
            return super().tearDown()

    def test_delete_customer(self):
        response = client.delete('http://localhost:8099/delete/customer/?customer_id=%s' % self.customer.id, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(models.Customer.objects.all()), 1)
        # gets user that suppose does not be existed.



class SingleNotificationTestCase(TestCase):

    def setUp(self) -> None:
        from . import models
        self.customer_data = {"username": "Nsfr", "email": "NeEalAdfss@gmail.com"}
        self.notification_data = {"message": "New Message."}
        self.customer = models.Customer.objects.create(**self.customer_data)
        self.notification = models.Notification.objects.create(**self.notification_data,
        status='SUCCESS', identifier='test-identifier', receiver=self.customer.notify_token)

    def tearDown(self):
        import django.core.exceptions
        try:
            customer = models.Customer.objects.get(id=self.customer.id)
            customer.delete()
        except(django.core.exceptions.ObjectDoesNotExist,):
            pass
        finally:
            return super().tearDown()

    def test_send_single_notification(self):

        response = client.post('http://localhost:8000/send/single/notification/',
        data={'customer_id': self.customer.id,
        'body': self.notification_data,
        'title': 'Test Title', 'topic': 'new_topic'}, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)


    def test_get_notifications(self):
        response = client.get('http://localhost:8000/get/notifications/',
        data={'customer_id': self.customer.id}, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('notifications', json.loads(response.read()).keys())

    def test_get_notification(self):
        response = client.get('http://localhost:8000/get/notification/',
        data={'customer_id': self.customer.id, 'notification_id': self.notification.id}, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertIn('notification', json.loads(response.read()).keys())

# import pika.callback
#
# class RabbitMQHeaders(dict):
#
#     def __enter__(self, *args, **kwargs):
#         assert all([element in () for element in kwargs.keys()])
#         assert all([value.upper() in () for value in list(kwargs.values())])
#         return kwargs
#
#
# class TestRabbitmqQueueEvent(object):
#
#     def __init__(self, queue, method, properties: pika.BasicProperties):
#
#         try:
#             self.queue: str = queue
#             self.method: str = method
#             self.properties = pika.BasicProperties(
#             content_type='application/json',
#             headers=RabbitMQHeaders(**properties.headers))
#         except(AssertionError,):
#             raise ValueError

# class RabbitMQIntegrationTestCase(TestCase):
#
#     def setUp(self) -> None:
#         from . import rabbitmq
#         self.rabbitmq_handler = rabbitmq.CustomerRabbitMQMessageHandler
#
#     @pytest.fixture(scope='module')
#     def connection_channel(self):
#         from . import rabbitmq
#         yield rabbitmq.RabbitMQConnection.connect_to_server()
#
#     def send_event(self):
#         pass
#
#     def test_connection(self, connection_channel):
#         pass
#
#     def test_queues(self, connection_channel):
#         pass
#
#     @unittest.mock.patch('main.test.send_event', autospec=True)
#     def test_callback(self, event):
#         self.mocked_event = event
#         self.rabbitmq_handler.handle_customer_message(queue=event.queue,
#         method=event.method, properties=event.properties, body=event.body)
#         self.assertGreater(len(models.Customer.objects.all()), 0)
#
#
# class RabbitMQTransactionIntegrationTestCase(unittest.TestCase):
#
#     def setUp(self) -> None:
#         from . import rabbitmq
#         self.CustomerHandler = rabbitmq.CustomerRabbitMQMessageHandler
#         self.RabbitmqConnection = rabbitmq.RabbitMQConnection
#
#     @pytest.fixture(scope='module')
#     def connection(self):
#         yield self.RabbitmqConnection.connect_to_server()
#
#     def handle_response(self, queue, method, properties, body, connection):
#
#         connection.close()
#         self.assertEquals(self.rabbitmq_event_object['body'], body)
#         self.assertEquals(self.rabbitmq_eventobject['queue'], queue.method.queue)
#         self.assertEquals(self.rabbitmq_event_object['method'], method)
#
#     @pytest.fixture(scope='module')
#     def rabbitmq_event(self):
#         event = {'properties': pika.BasicProperties(headers={'METHOD': 'POST'}),
#         'queue': 'customer_queue', 'method': 'method', 'body': {}}
#         return event
#
#     def test_react_on_failure_event(self, rabbitmq_event, connection):
#
#         self.rabbitmq_event_object = rabbitmq_event
#         self.CustomerHandler.handle_customer_message(**mocked_event)
#
#         connection.basic_consume(on_message_callback=self.handle_response)
#         connection.start_consuming()
#
#         self.assertRaises(NotImplementedError)
#