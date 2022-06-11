import firebase_admin, pytest
import firebase_admin.auth
from django.test import TestCase
from django import test
import parameterized.parameterized
import django.conf

from rest_framework import status
from . import models
from django.conf import settings

client = test.Client()

class TestFireBaseMixin(object):

    def set_notify_token(self, customer_data):
        import firebase_admin._auth_utils
        try:
            import firebase_admin.auth, datetime, uuid
            generated_uid = str(uuid.uuid4()) + '%s' % datetime.datetime.now()
            # / * generates unique identifier for
            # notification client based on user creation data.
            firebase_customer = firebase_admin.auth.create_user(display_name=customer_data.get('username'),
            email=customer_data.get('email'), app=getattr(models, 'application'), disabled=False, uid=generated_uid,
            email_verified=True)
            generated_token = auth.create_custom_token(uid=firebase_customer.uid,
            app=getattr(models, 'application'))
            return generated_token

        except(firebase_admin._auth_utils.EmailAlreadyExistsError,):
            return firebase_admin.auth.get_user_by_email(
            email=customer_data.get('email'), app=getattr(models, 'application')).uid

    def tearDown(self):
        try:
            uid = self.customer.uid if hasattr(self, 'customer') else None
            firebase_admin.auth.delete_user(uid=uid, app=getattr(models, 'application'))
        except(firebase_admin._auth_utils.UserNotFoundError,):
            pass
        finally:
            return super().tearDown()

class CustomerAPITestCase(TestFireBaseMixin, TestCase):

    def setUp(self) -> None:

        self.customer_data = {'username': 'NewUser', 'email': 'new_email@gmail.com'}
        self.customer_data['notify_token'] = self.set_notify_token(customer_data=self.customer_data)
        self.customer = models.Customer.objects.create(**self.customer_data)

    @parameterized.parameterized.expand([{"username": "AnotherUser"}])
    def test_create_customer(self, customer_data):

        response = client.post('http://localhost:8000/create/customer/',
        data=customer_data, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Customer.objects.all()), 1)

    @parameterized.parameterized.expand([{"username": "AnotherNewUser"}])
    def test_update_customer(self, updated_data):
        response = client.put('http://localhost:8000/update/customer/',
        data=updated_data, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_delete_customer(self):
        response = client.delete('http://localhost:8099/delete/customer/',
        params={'customer_id': self.customer.id}, timeout=10)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertLess(len(models.Customer.objects.all()), 1)
        # gets user that suppose does not be existed.


class SingleNotificationTestCase(TestFireBaseMixin, TestCase):

    def setUp(self) -> None:
        self.customer_data = {"username": "NeqUser", "email": "NewEmailAddress@gmail.com"}
        self.notification_data = {"message": "New Message."}
        self.customer_data['notify_token'] = self.set_notify_token(customer_data=self.customer_data)
        self.customer = models.Customer.objects.create(**self.customer_data)

    def test_send_single_notification(self):

        response = client.post('http://localhost:8000/send/single/notification/',
        data={'customer_id': self.customer.notify_token,
        'notification_payload': self.notification_data,
        'title': 'Test Title'}, timeout=10)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(models.Notification.objects.all()), 1)
