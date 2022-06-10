from __future__ import annotations
import typing

import firebase_admin.auth, firebase_admin.exceptions
from firebase_admin import messaging
from . import models


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


class NotificationRequest(object):

    def __init__(self, body: dict, title: str,
    to: typing.Optional[typing.List[NotifyToken | str] | str | NotifyToken]):

        self.body = body
        self.title = title
        self.to = [to] if not iter(to) else to
        self.topic = 'notifications'

    def send_notification(self):

        notification = messaging.Notification(self.title, self.body)
        messages = [messaging.Message(notification=notification, token=token) for token in self.to]
        sended = messaging.send_all(messages=messages)
        if not len(sended.success_count) == len(self.to):
            logger.debug('failed to send all notifications.')
            raise NotImplementedError



