from __future__ import annotations
import typing

import firebase_admin
from firebase_admin import messaging
from . import models


class NotificationRequest(object):

    def __init__(self, body, title, to: typing.Optional[typing.List[str] | str]):
        self.body = body
        self.title = title
        self.to = [to] if not iter(to) else to
        self.topic = ''

    def __call__(self, *args, **kwargs):
        customer = models.Customer.objects.get(id=kwargs.get('id'))
        if not customer.is_notified:
            self.subscribe_to_notifications(customer_token=customer.notify_token,
            topic=self.topic)

    @staticmethod
    def subscribe_to_notifications(customer_token, topic):
        from . import models
        yield messaging.subscribe_to_topic(tokens=[customer_token],
        topic=topic, app=getattr(models, 'app'))

    def send_notification(self):

        notification = messaging.Notification(self.title, self.body)
        messages = [messaging.Message(notification=notification, token=token) for token in self.to]
        messaging.send_all(messages=messages)

    def check_delivered(self):
        pass



