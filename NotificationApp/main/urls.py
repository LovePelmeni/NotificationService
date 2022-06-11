from . import views
from django.urls import path

app_name = 'main'

urlpatterns = [

    path('get/notification/', views.NotificationViewSet.as_view({'get': 'retrieve'})),
    path('get/notifications/', views.NotificationViewSet.as_view({'get': 'list'})),
    path('create/notification/', views.NotificationViewSet.as_view({'get': 'create'})),

]

customer_urlpatterns = [

    path('create/customer/', views.CreateCustomer.as_view(), name='create-customer'),
    path('update/customer/', views.UpdateCustomer.as_view(), name='update-customer'),
    path('delete/customer/', views.DeleteCustomer.as_view(), name='delete-customer')

]

schema_urlpatterns = [

]

urlpatterns += customer_urlpatterns
urlpatterns += schema_urlpatterns


