from rest_framework import authentication
from django.utils import deprecation

class UserAuthenticationClass(authentication.BaseAuthentication):

    def get_authenticate_header(self, request):
        pass

    def authenticate(self, request):
        pass

class SetAuthHeaderMiddleware(deprecation.MiddlewareMixin):

    def process_request(self, request):
        pass