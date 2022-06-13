import drf_yasg.openapi

from . import views
from django.urls import path
import django.http
import drf_yasg.views as drf_yasg_views, drf_yasg.openapi
from rest_framework import permissions

app_name = 'main'

urlpatterns = [

    path('get/notification/', views.NotificationSingleViewSet.as_view({'get': 'retrieve'})),
    path('get/notifications/', views.NotificationSingleViewSet.as_view({'get': 'list'})),

    path('send/single/notification/', views.NotificationSingleViewSet.as_view({'post': 'create'})),
    path('send/multi/notification/', views.NotificationMultiUserViewSet.as_view({'post': 'create'})),

]

customer_urlpatterns = [

    path('create/customer/', views.CustomerGenericAPIView.as_view({'post': 'create'}), name='create-customer'),
    path('delete/customer/', views.CustomerGenericAPIView.as_view({'delete': 'destroy'}), name='delete-customer')

]

healthcheck_urlpatterns = [

    path('healthcheck/', lambda request: django.http.HttpResponse(status=200), name='healthcheck'),

]

schema = drf_yasg_views.get_schema_view(
        info=drf_yasg.openapi.Info(
        title='Notification Service',
        description='Service, for handling notifications.',
        default_version='1.0',
        contact=drf_yasg.openapi.Contact('kirklimushin@gmail.com'),
        license=drf_yasg.openapi.License('BSD License'),
    ),
    public=True,
    permission_classes = (permissions.AllowAny,)
)

schema_urlpatterns = [

    path('swagger/', schema.with_ui('swagger', cache_timeout=0), name='schema-view'),
    path('redoc/', schema.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]

urlpatterns += customer_urlpatterns
urlpatterns += schema_urlpatterns
urlpatterns += healthcheck_urlpatterns




