from django.contrib import admin
from . import models
# Register your models here.

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display = ('status', "identifier",)
    fields = ('status', 'identifier',)


@admin.register(models.Customer)
class NotificationCustomerAdmin(admin.ModelAdmin):

    list_display = ('username', 'email',)
    fields = ('username', 'email')



