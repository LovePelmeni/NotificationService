from __future__ import annotations
import typing, pydantic

from django.conf import settings
import django.db.utils

import firebase_admin.auth, firebase_admin.exceptions
from firebase_admin import messaging
from django.db import transaction

from . import models, certificate
import logging
from django.conf import settings


logger = logging.getLogger(__name__)


class InvalidNotifyToken(Exception):
    pass


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


def check_valid_token(token: str) -> bool:
    import requests
    try:
        response = requests.post('https://fcm.googleapis.com/fcm/send',
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s'
            % getattr(settings, 'WEB_API_KEY')}, timeout=10, data={'registration_ids': '[%s]' % token})
        if not response.status_code in (200, 201):
            return False
        return True
    except() as exception:
        logger.debug('invalid token: %s' % exception)
        raise firebase_admin.exceptions.InternalError(message='Invalid FCM Token')


class NotificationMultiRequest(object):
    """/ * Class Represents Interface for sending out
    one/to/many and many/to/one notification against user/s"""

    def __init__(self, receivers: typing.List[NotifyToken], body: dict, status='OK', title='Notification'):
        try:
            self.status = status
            self.receivers = receivers
            self.body = body
            self.title = title
            assert 'message' in self.body.keys()
        except(KeyError, AssertionError):
            raise NotImplementedError

    def send_one_to_many_notification(self):

        notification = messaging.Notification(title=self.title, body=self.body)
        message = messaging.MulticastMessage(data=self.body,
        notification=notification, tokens=[receiver.token for receiver in self.receivers])

        sended_response = messaging.send_multicast(multicast_message=message,
        app=getattr(models, 'application'))

        if sended_response.failure_count:
            logger.debug('failed to send message: "%s". to all Members.' % self.body['message'])
            raise NotImplementedError

        models.Notification.objects.using(settings.MAIN_DATABASE).create(**{'identifier':
        sended_identifier, 'message': self.body['message'], 'receiver': json.dumps(self.receivers)})


class NotificationSingleRequest(object):
    """
    / * Class Represents Interface responsible for sending single notification to single user.
    """

    def __init__(self, body: str | dict, title: str,
    to: NotifyToken, topic: typing.Optional[str]):
        import json
        try:
            self.body = json.loads(body) if isinstance(body, str) else body
            self.title = title
            self.token = to.token if hasattr(to, 'token') else None
            self.topic = topic

        except(AssertionError, InvalidNotifyToken, AttributeError, json.decoder.JSONDecodeError,):
            raise NotImplementedError


    def get_authorized_session(self):

        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
        credentials = service_account.Credentials.from_service_account_info(
        info=getattr(certificate, 'CERTIFICATE_CREDENTIALS'), scopes=SCOPES)
        session = AuthorizedSession(credentials=credentials)
        yield session


    def send_notification(self):
        import requests.exceptions
        try:
            from . import models
            import json

            message = json.dumps({
                "message": {
                    "topic": self.topic,
                    "token": self.token,
                    "notification": {
                        'title': self.title,
                        'body': self.body.get('message'),
                    },
                },
            })

            with self.get_authorized_session() as session:
                response = session.request(method='post',
                    url='https://fcm.googleapis.com/v1/projects/%s/messages:send'
                    % getattr(certificate, 'CERTIFICATE_CREDENTIALS')['project_id'],
                    headers={'Content-Type': 'application/json'},
                    timeout=10, data=message
                )
                response.raise_for_status()

            try:
                with transaction.atomic():
                    status = 'SUCCESS' if str(response.status_code) in ('200', '201') else 'ERROR'
                    assert status not in ('ERROR', 'FAILED')
                    models.Notification.objects.using(settings.MAIN_DATABASE).create(
                        **{'identifier': json.loads(response.text)['name'],
                        'message': self.body['message'],
                        'receiver': self.to,
                        'status': status
                    })

            except(AssertionError,):
                transaction.rollback()

        except(ValueError, NotImplementedError,
        django.db.utils.InternalError, django.db.utils.IntegrityError, requests.exceptions.HTTPError) as exception:
            logger.debug('%s' % exception)
            raise NotImplementedError


