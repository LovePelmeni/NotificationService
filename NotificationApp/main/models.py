from django.db import models
import firebase_admin
import django.dispatch.dispatcher

import django.core.exceptions
from firebase_admin import messaging

# Create your models here.


status_choices = [
    ('ERROR', 'error'),
    ('SUCCESS', 'success'),
    ('INFO', 'info')
]


credentials = firebase_admin.credentials.Certificate(cert='')
application = firebase_admin.initialize_app(credential=credentials)


UserCreated = django.dispatch.dispatcher.Signal()
UserDeleted = django.dispatch.dispatcher.Signal()


@django.dispatch.dispatcher.receiver(UserCreated)
def create_firebase_customer(customer_data, **kwargs):
    pass

@django.dispatch.dispatcher.receiver(UserDeleted)
def delete_firebase_customer(customer_id, **kwargs):
    pass

class Notification(models.Model):

    objects = models.Manager()

    message = models.CharField(verbose_name='Message', max_length=100)
    status = models.CharField(choices=status_choices, max_length=10)
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
            messaging.subscribe_to_topic(tokens=[customer_token],
            topic=getattr(models, 'topic'), app=getattr(models, 'app'))
            return user
        except(django.db.utils.IntegrityError,) as exception:
            raise exception

    def delete(self, **kwargs):
        try:
            messaging.subscribe_to_topic(tokens=[kwargs.get('customer_token')],
            topic=getattr(models, 'topic'), app=getattr(models, 'app'))
            return super().delete()
        except(django.db.utils.IntegrityError,
        django.core.exceptions.ObjectDoesNotExist) as exception:
            raise exception



class CustomerManager(django.db.models.manager.BaseManager.from_queryset(queryset_class=CustomerQueryset)):
    pass


class Customer(models.Model):

    objects = CustomerManager()

    username = models.CharField(verbose_name='Username', max_length=100, unique=True)
    notify_token = models.CharField(verbose_name='Notify Token', max_length=100, null=False, editable=False)
    notifications = models.ForeignKey(Notification,
    on_delete=models.CASCADE, related_name='owner', null=True)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username



