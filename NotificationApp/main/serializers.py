import typing
import django.core.exceptions
import firebase_admin.auth
from rest_framework import serializers
from . import models, notification_api


class CustomerSerializer(serializers.ModelSerializer):

    username = serializers.CharField(label='Username', max_length=100, required=True)
    email = serializers.EmailField(label='Email', max_length=100, required=True)
    notify_token = serializers.CharField(label='Registration Token', max_length=128, required=True)

    def validate_username(self, username):
        if not username in  models.Customer.objects.values_list('username', flat=True):
            return username
        raise django.core.exceptions.ValidationError(message='Invalid Username.')

    def validate_email(self, email):
        import django.core.exceptions
        try:
            if firebase_admin.auth.get_user_by_email(email=email,
            app=getattr(models, 'application')):
                message = 'Email already exists in firebase.'
                raise django.core.exceptions.ValidationError(message=message)

        except(firebase_admin._auth_utils.UserNotFoundError,):
            return email
        except(django.core.exceptions.ValidationError) as exception:
            raise exception

    def validate_notify_token(self, token):
        import firebase_admin.auth
        if not token in models.Customer.objects.values_list('notify_token', flat=True) \
        and notification_api.check_valid_token(token):
            return token
        raise django.core.exceptions.ValidationError(message='Invalid Token.')


    class Meta:
        model = models.Customer
        fields = ('username', "email",)




