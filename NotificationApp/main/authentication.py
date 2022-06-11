from rest_framework import authentication
from django.utils import deprecation
import django.core.exceptions, jwt

class UserAuthenticationClass(authentication.BaseAuthentication):

    def get_authenticate_header(self, request):
        return request.META.get('Authorization')

    def authenticate(self, request):
        if not self.get_authenticate_header(request):
            raise django.core.exceptions.PermissionDenied()
        try:
            token = self.get_authenticate_header(request).split(' ')[1]
            jwt.decode(token, algorithm='HS256', key=getattr(settings, 'SECRET_KEY'))
            return None
        except(jwt.PyJWTError,):
            raise django.core.exceptions.PermissionDenied()


class SetAuthHeaderMiddleware(deprecation.MiddlewareMixin):

    def process_request(self, request):
        try:
            if not 'Authorization' in request.META.keys():
                jwt_token = request.get_signed_cookie('jwt-token')
                request.META['Authorization'] = 'Bearer %s' % jwt_token
            return None
        except(KeyError,):
            return None


