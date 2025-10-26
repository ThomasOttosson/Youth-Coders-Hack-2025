from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.Event)
admin.site.register(models.EventAttendee)
admin.site.register(models.EventCategory)
admin.site.register(models.EventInvitation)
