import firebase_admin, pytest
import firebase_admin.auth
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



