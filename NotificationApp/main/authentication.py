from rest_framework import authentication
from django.utils import deprecation

class UserAuthenticationClass(authentication.BaseAuthentication):

    def get_authenticate_header(self, request):
        return request.META.get('Authorization')

    def authenticate(self, request):
        pass

class SetAuthHeaderMiddleware(deprecation.MiddlewareMixin):

    def process_request(self, request):
        try:
            if not 'Authorization' in request.META.keys():
                jwt = request.get_signed_cookie('jwt-token')
                request.META['Authorization'] = 'Bearer %s' % jwt
            return None
        except(KeyError,):
            return None



