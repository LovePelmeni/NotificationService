import firebase_admin.auth
from rest_framework import serializers
from . import models


class CustomerSerializer(serializers.ModelSerializer):

    username = serializers.CharField(label='Username', max_length=100, required=True)
    email = serializers.EmailField(label='Email', max_length=100, required=True)

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

    class Meta:
        model = models.Customer
        fields = ('username', "email",)


class CustomerUpdateSerializer(CustomerSerializer):

    def __init__(self, **kwargs):
        super(CustomerSerializer, self).__init__(**kwargs)
        del self.fields['email']

    def validate(self, attrs: dict):
        for element, value in attrs.items():
            if not self.validated_data[element] in \
            models.Customer.objects.values_list('username', flat=True):
                continue
        return attrs




