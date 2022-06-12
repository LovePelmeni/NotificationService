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


client = test.Client()
logger = logging.getLogger(__name__)


class TestFireBaseMixin(object):

    def tearDown(self):
        try:
            uid = self.customer.notify_token if hasattr(self, 'customer') else None
            firebase_admin.auth.delete_user(uid=uid, app=getattr(models, 'application'))
        except(firebase_admin._auth_utils.UserNotFoundError,):
            pass
        finally:
            return super().tearDown()


class CustomerAPITestCase(TestFireBaseMixin, TestCase):

    def setUp(self) -> None:

        self.customer_data = {'username': 'Ndfdfsdfsr', 'email': 'nw_edsfal@gmail.com'}
        self.customer = models.Customer.objects.get_or_create(**self.customer_data, defaults=self.customer_data)[0]
        self.another_customer_data = {'username': 'AnodsfterUser', "email": "anothersdfs_mail@gmail.com"}


    def test_create_customer(self):

        response = client.post('http://localhost:8000/create/customer/',
        data=self.another_customer_data, timeout=10)
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertGreater(len(models.Customer.objects.all()), 1)

    @parameterized.parameterized.expand([{"username": "AnthdsffderewUser", "email": "AnothesdsfdfdsdfrEmail@gmail.com"}])
    def test_update_customer(self, updated_data):
        response = client.put('http://localhost:8000/update/customer/?customer_id=%s' % self.customer.id,
        data=updated_data, timeout=10)
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_delete_customer(self):
        response = client.delete('http://localhost:8099/delete/customer/?customer_id=%s' % self.customer.id, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(models.Customer.objects.all()), 1)
        # gets user that suppose does not be existed.


class SingleNotificationTestCase(TestFireBaseMixin, TestCase):

    def setUp(self) -> None:
        self.customer_data = {"username": "Neddfdffdsfr", "email": "NeEalAdddfdfredfdsfss@gmail.com"}
        self.notification_data = {"message": "New Message."}
        self.customer = models.Customer.objects.get_or_create(**self.customer_data, defaults=self.customer_data)[0]

    def test_send_single_notification(self):

        response = client.post('http://localhost:8000/send/single/notification/',
        data={'customer_id': self.customer.id,
        'notification_payload': self.notification_data,
        'title': 'Test Title'}, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)






