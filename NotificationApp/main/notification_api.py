from __future__ import annotations
import typing

import firebase_admin.auth, firebase_admin.exceptions
from firebase_admin import messaging

from . import models
import logging

logger = logging.getLogger(__name__)

class NotifyToken(object):
    """
    / * Class Represents customer notification token.
    """

    def __init__(self, token: str):
        self.token = token

    def __call__(self, *args, **kwargs):
        return self.validate()

    def validate(self) -> str | Exception:
        try:
            firebase_admin.auth.get_user(uid=self.user_token)
            return self.user_token
        except(firebase_admin.exceptions.NotFoundError):
            raise firebase_admin.exceptions.NotFoundError(
            message=json.dumps({'error': 'Your Token Is Expired. %s' % self.user_token}))


class InvalidNotifyToken(Exception):
    pass


class NotificationMultiRequest(object):
    """/ * Class Represents Interface for sending out
    one/to/many and many/to/one notifications against user/s"""

    def __init__(self, receivers: typing.List[NotifyToken], body: dict, status='OK', title='Notification'):
        try:
            self.status = status
            self.receivers = receivers
            self.body = body
            self.title = title
            assert 'message' in self.body.keys()
        except(KeyError, AssertionError):
            raise NotImplementedError

    def send_many_to_many_notification(self):
        pass


    def send_one_to_many_notification(self):

        notification = messaging.Notification(title=self.title, body=self.body)
        message = messaging.MulticastMessage(data=self.body,
        notification=notification, tokens=[receiver.token for receiver in self.receivers])

        sended_response = messaging.send_multicast(multicast_message=message,
        app=getattr(models, 'application'))

        if sended_response.failure_count:
            logger.debug('failed to send message: "%s". to all Members.' % self.body['message'])
            raise NotImplementedError

        models.NotificationCreated.send(self, {'identifier':
        sended_identifier, 'message': self.body['message'], 'receiver': json.dumps(self.to)})


class NotificationSingleRequest(object):
    """
    / * Class Represents Interface responsible for sending single notification to single user.
    """

    def __init__(self, body: dict, title: str,
    to: NotifyToken):

        try:
            self.body = body
            self.title = title
            self.to = to.token if hasattr(to, 'notify_token') else None
            self.topic = 'notifications'
            assert 'message' in body.keys()

        except(AssertionError, InvalidNotifyToken, AttributeError):
            raise NotImplementedError

    def send_notification(self):
        try:
            from . import models
            notification = messaging.Notification(title=self.title, body=self.body)
            messages = messaging.Message(notification=notification, token=self.to, topic=self.topic)
            sended_identifier = messaging.send(message=messages, app=getattr(models, 'application'))
            logger.debug('failed to send all notifications.')
            models.NotificationCreated.send(self, {'identifier':
            sended_identifier, 'message': self.body['message'], 'receiver': self.to})

        except(ValueError, NotImplementedError,):
            raise NotImplementedError




