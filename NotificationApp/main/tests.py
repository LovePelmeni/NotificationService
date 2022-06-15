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
import django.core.exceptions


client = test.Client()
logger = logging.getLogger(__name__)
#
# class CustomerAPITestCase(TestCase):
#
#     def setUp(self) -> None:
#         import rest_framework.exceptions
#         try:
#             self.customer_data = {'username': 'dfr', 'email': 'nfl@gmail.com'}
#             self.customer = models.Customer.objects.create(**self.customer_data)
#             self.another_customer_data = {'username': 'Anser', "email": "anofs_il@gmail.com"}
#
#         except(rest_framework.exceptions.ValidationError,):
#             raise NotImplementedError()
#
#     def test_create_customer(self):
#
#         response = client.post('http://localhost:8000/create/customer/',
#         data=self.another_customer_data, timeout=10)
#         self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
#         self.assertGreater(len(models.Customer.objects.all()), 1)
#
#     def tearDown(self):
#         try:
#             models.Customer.objects.get(id=self.customer.id).delete()
#         except(firebase_admin._auth_utils.UserNotFoundError,):
#             pass
#         finally:
#             return super().tearDown()
#
#     def test_delete_customer(self):
#         response = client.delete('http://localhost:8099/delete/customer/?customer_id=%s' % self.customer.id, timeout=10)
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertLess(len(models.Customer.objects.all()), 1)
#         # gets user that suppose does not be existed.
#
#
#
# class SingleNotificationTestCase(TestCase):
#
#     def setUp(self) -> None:
#         from . import models
#         self.customer_data = {"username": "Nsfr", "email": "NeEalAdfss@gmail.com"}
#         self.notification_data = {"message": "New Message."}
#         self.customer = models.Customer.objects.create(**self.customer_data)
#         self.notification = models.Notification.objects.create(**self.notification_data,
#         status='SUCCESS', identifier='test-identifier', receiver=self.customer.notify_token)
#
#     def tearDown(self):
#         import django.core.exceptions
#         try:
#             customer = models.Customer.objects.get(id=self.customer.id)
#             customer.delete()
#         except(django.core.exceptions.ObjectDoesNotExist,):
#             pass
#         finally:
#             return super().tearDown()
#
#     def test_send_single_notification(self):
#
#         response = client.post('http://localhost:8000/send/single/notification/',
#         data={'customer_id': self.customer.id,
#         'body': self.notification_data,
#         'title': 'Test Title', 'topic': 'new_topic'}, timeout=10)
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertGreater(len(models.Notification.objects.all()), 1)
#
#
#     def test_get_notifications(self):
#         response = client.get('http://localhost:8000/get/notifications/',
#         data={'customer_id': self.customer.id}, timeout=10)
#
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertIn('notifications', json.loads(response.read()).keys())
#
#
#     def test_get_notification(self):
#         response = client.get('http://localhost:8000/get/notification/',
#         data={'customer_id': self.customer.id, 'notification_id': self.notification.id}, timeout=10)
#         self.assertEquals(response.status_code, status.HTTP_200_OK)
#         self.assertIn('notification', json.loads(response.read()).keys())
#

if settings.INDEPENDENT_SERVICE:

    class RabbitMQIntegrationServiceTestCase(TestCase):

        def test_connection_established(self):
            try:
                from . import rabbitmq
                with rabbitmq.RabbitMQConnection.connect_to_server() as connection:
                    connection.close()
            except(pika.exceptions.AMQPChannelError, pika.exceptions.ChannelError,):
                raise NotImplementedError


    class ObjectRecovered(Exception):
        pass

    class ObjectDeleted(Exception):
        pass

    class ObjectCreated(Exception):
        pass

    class Skipped(Exception):
        pass

    class RabbitMQCustomerIntegrationTestCase(TestCase):

        def setUp(self) -> None:
            import collections.abc
            from . import rabbitmq
            self.rabbitmq_handler = rabbitmq.CustomerRabbitMQMessageHandler
            self.mock_attrs = ("queue", "method", "properties", "body")

        @pytest.fixture(scope='module')
        def connection_channel(self):
            from . import rabbitmq
            yield rabbitmq.RabbitMQConnection.connect_to_server()


        def test_post_customer_failure_rollback(self):

            mocked_event = unittest.mock.Mock()
            mocked_event.body.return_value = {'username': 'Customer', 'email': 'Email'}
            mocked_event.properties.return_value = pika.BasicProperties(
            headers={"METHOD": 'POST', 'sender': 'SomeService'})

            with unittest.mock.patch('.rabbitmq.models.Customer.objects.using') as mocked_queue_message:
                mocked_queue_message.delete.side_effect = ObjectDeleted

                with self.assertRaises(ObjectDeleted):

                    self.rabbitmq_handler.handle_customer_failure_queue_messages(queue=mocked_event.queue,
                    method=mocked_event.method, properties=mocked_event.properties, body=mocked_event.body)
                    self.assertNoLogs(logger, level='ERROR')
                    self.assertEquals(len(models.Customer.objects.using(
                    setting.MAIN_DATABASE).all()), initial_query)



        def test_delete_customer_failure_rollback(self):

            mocked_event = unittest.mock.Mock()
            initial_query = len(models.Customer.objects.using(settings.MAIN_DATABASE).all())

            mocked_event.queue.return_value = 'customer_failure_queue'
            mocked_event.method.return_value = 'method'
            mocked_event.body.return_value = {'username': 'Customer', 'email': 'Email'}
            mocked_event.properties.return_value = pika.BasicProperties(headers={"METHOD": 'POST', 'sender': 'SomeService'})


            with unittest.mock.patch('.rabbitmq.models.Customer.objects.using') as mocked_queue_message:
                mocked_queue_message.create.side_effect = ObjectRecovered

                with self.assertRaises(ObjectRecovered):

                    self.rabbitmq_handler.handle_customer_failure_queue_messages(queue=mocked_event.queue,
                    method=mocked_event.method, properties=mocked_event.properties, body=mocked_event.body)
                    self.assertNoLogs(logger, level='ERROR')
                    self.assertGreater(len(models.Customer.objects.using(
                    setting.MAIN_DATABASE).all()), initial_query)


                event.properties.return_value.headers.update({'sender': 'NotificationService'})

                with unittest.mock.patch(target='builtins.pass', autospec=True) as mocked_failure_msg:
                    mocked_failure_msg.side_effect = Skipped

                    with self.assertRaises(expected_exception=Skipped):
                        self.rabbitmq_handler.handle_customer_failure_queue_messages(
                        mocked_event.queue, mocked_event.body, mocked_event.method, mocked_event.properties)
                        mocked_failure_msg.assert_called_once()


        def test_post_customer_success_callback(self):

            mocked_event = unittest.mock.Mock()
            initial_query = len(models.Customer.objects.using(settings.MAIN_DATABASE).all())

            mocked_event.queue.return_value = 'customer_failure_queue'
            mocked_event.method.return_value = 'method'
            mocked_event.body.return_value = {'username': 'Customer', 'email': 'Email'}
            mocked_event.properties.return_value = pika.BasicProperties(
            headers={"METHOD": 'POST', 'sender': 'SomeService'})


            with unittest.mock.patch('.rabbitmq.models.Customer.object.using') as mocked_transaction:
                mocked_transaction.create.side_effect = ObjectCreated

                with self.assertRaises(expected_exception=ObjectCreated):

                    self.rabbitmq_handler.handle_customer_queue_messages(mocked_event.queue,
                    mocked_event.method, mocked_event.properties, mocked_event.body)
                    self.assertNoLogs(logger, level='ERROR')
                    self.assertGreater(len(models.Customer.objects.using(
                    settings.MAIN_DATABASE).all()), initial_query)


        def test_delete_customer_success_callback(self):

            mocked_event = unittest.mock.Mock()
            initial_query = len(models.Customer.objects.using(settings.MAIN_DATABASE).all())


            mocked_event.queue.return_value = 'customer_queue'
            mocked_event.method.return_value = 'method'

            mocked_event.body.return_value = {'username': 'Customer', 'email': 'Email'}
            mocked_event.properties.return_value = pika.BasicProperties(
                headers={"METHOD": 'DELETE', 'sender': 'SomeService'})

            with unittest.mock.patch('.rabbitmq.models.Customer.object.using') as mocked_transaction:
                mocked_transaction.delete.side_effect = ObjectDeleted

                with self.assertRaises(expected_exception=ObjectDeleted):
                    self.rabbitmq_handler.handle_customer_queue_messages(
                    properties=mocked_event.properties, body=mocked_event.body,
                    method=mocked_event.method, queue=mocked_event.queue)
                    self.assertNoLogs(logger, level='ERROR')
                    self.assertLess(len(models.Customer.objects.using(
                    settings.MAIN_DATABASE).all()), initial_query)




