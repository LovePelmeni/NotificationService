import firebase_admin
from django.test import TestCase
from django import test

from rest_framework import status
from . import models

# Create your tests here.
app = firebase_admin.initialize_app(
credential=firebase_admin.credentials.Certificate('cert.json'))
notification = {}

class TestNotificationAPICase(TestCase):

    def setUp(self) -> None:
        self.notification = {}

    @pytest.fixture(scope='module')
    def client(self):
        yield test.Client()

    @pytest.fixture(scope='module')
    def notification_client(self):
        from . import models
        customer_data = {}
        user = models.Customer.objects.create(**customer_data)
        yield user.notify_token

    @staticmethod
    @pytest.fixture(scope='session', autouse=True)
    def check_for_notification_errors(notification_client):
        from firebase_admin import messaging
        topic_response = messaging.subscribe_to_topic(tokens=[notification_client],
        topic='notification', app=app)
        assert not topic_response.errors

    def test_create_notification(self, client):
        response = client.post('http://localhost:8099/send/notification/',
        data=self.notification, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)


class CustomerAPITestCase(TestCase):

    def setUp(self) -> None:

        self.customer_data = {}
        self.customer = models.Customer.objects.create(**self.customer_data)

    def create_customer(self, client):
        response = client.post('http://localhost:8000/create/customer/', timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Customer.objects.all()), 1)

    @parameterized.parameterized.expand([{'username': 'New Nickname'}])
    def update_customer(self, updated_data, client=None):
        response = client.put('http://localhost:8000/update/customer/',
        data=updated_data, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)


    def delete_customer(self, client):
        response = client.delete('http://localhost:8099/delete/customer/',
        params={'customer_id': self.customer.id}, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(models.Customer.objects.all()), 1)


