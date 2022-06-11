import firebase_admi, pytest
import firebase_admin.auth
from django.test import TestCase
from django import test

from rest_framework import status
from . import models

# Create your tests here.
app = firebase_admin.initialize_app(
credential=firebase_admin.credentials.Certificate('cert.json'))
notification = {}

# module tests:

class TestNotificationAPICase(TestCase):

    def setUp(self) -> None:

        self.notification = {}
        self.customer_data = {'username': 'SomeUser',
        'email': 'some_email@gmail.com', 'password': 'SomePassword'}

        self.customer_token = models.Customer.objects.create(
        **self.customer_data).notify_token

        self.notification_payload = {}
        self.title = 'Test Notification'

    @pytest.fixture(scope='module')
    def client(self):
        yield test.Client()

    def test_create_notification(self, client):

        response = client.post('http://localhost:8099/send/notification/',
        data={'notification_payload': self.notification_payload,
        'title': self.title}, timeout=10, params={'customer_token': self.customer_token})
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)


class CustomerAPITestCase(TestCase):

    def setUp(self) -> None:

        self.customer_data = {}
        self.customer = models.Customer.objects.create(**self.customer_data)

    @parameterized.parameterized.expand([client, {'email': 'test_email@gmail.com'}])
    def create_customer(self, client, test_customer_data):

        response = client.post('http://localhost:8000/create/customer/',
        data=test_customer_data, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Customer.objects.all()), 1)

        user = firebase_admin.auth.get_user_by_email(email='test_email@gmail.com')
        self.assertIsNotNone(user)

    @parameterized.parameterized.expand([{'username': 'New Nickname'}, client])
    def update_customer(self, updated_data, client=None):
        response = client.put('http://localhost:8000/update/customer/',
        data=updated_data, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def delete_customer(self, client):
        response = client.delete('http://localhost:8099/delete/customer/',
        params={'customer_id': self.customer.id}, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(models.Customer.objects.all()), 1)

        firebase_customer = firebase_admin.auth.get_user_by_email(email=self.customer.email)
        # gets user that suppose does not be existed.
        self.assertRaises(firebase_admin._auth_utils.UserNotFoundError, firebase_customer)


class SingleNotificationTestCase(TestCase):

    def test_send_single_notification(self, client):

        response = client.post('http://localhost:8000/create/customer/',
        data={'customer_token': ''}, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)


class MultiReceiverNotificationTestCase(TestCase):

    def setUp(self) -> None:
        self.query = {}
        self.users = db_models.QuerySet(model=models.Customer, query={})
        self.receivers = [notification_api.NotifyToken(token=user.token) for user in self.users]
        self.notification = {}

    def send_multi_user_notification(self):
        pass

