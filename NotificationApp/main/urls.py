import drf_yasg.openapi

from . import views
from django.urls import path
from drf_yasg import *
import django.http
import drf_yasg.views, drf_yasg.openapi

app_name = 'main'

urlpatterns = [

    path('get/notification/', views.NotificationViewSet.as_view({'get': 'retrieve'})),
    path('get/notifications/', views.NotificationViewSet.as_view({'get': 'list'})),
    path('create/notification/', views.NotificationViewSet.as_view({'get': 'create'})),

]

customer_urlpatterns = [

    path('create/customer/', views.CustomerGenericAPIView.as_view({'post': 'create'}), name='create-customer'),
    path('update/customer/', views.CustomerGenericAPIView.as_view({'put': 'update'}), name='update-customer'),
    path('delete/customer/', views.CustomerGenericAPIView.as_view({'delete': 'destroy'}), name='delete-customer')

]

healthcheck_urlpatterns = [

    path('healthcheck/', lambda request: django.http.HttpResponse(status=200), name='healthcheck'),

]

schema = drf_yasg.views.get_schema_view(
        info=drf_yasg.openapi.Info(
        title='Notification Service',
        description='Service, for handling notifications.',
        default_version='1.0',
        contact=drf_yasg.openapi.Contact('kirklimushin@gmail.com'),
        license=drf_yasg.openapi.License('BSD License'),
    )
)
schema_urlpatterns = [

]

urlpatterns += customer_urlpatterns
urlpatterns += schema_urlpatterns
urlpatterns += healthcheck_urlpatterns

