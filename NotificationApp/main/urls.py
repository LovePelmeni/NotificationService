from . import views
from django.urls import path


urlpatterns = [

    path('', views.home, name='home'),
    path('get/notification/', views.NotificationViewSet.as_view({'get': 'retrieve'})),
    path('create/notification/', views.NotificationViewSet.as_view({'get': 'create'})),

]

customer_urlpatterns = [

    path('create/customer/', views.CreateCustomer.as_view(), name='create-customer'),
    path('update/customer/', views.UpdateCustomer.as_view(), name='update-customer'),
    path('delete/customer/', views.DeleteCustomer.as_view(), name='delete-customer')

]

urlpatterns += customer_urlpatterns