from django.contrib import admin
from . import models
# Register your models here.

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Customer)
class NotificationCustomerAdmin(admin.ModelAdmin):
    pass



