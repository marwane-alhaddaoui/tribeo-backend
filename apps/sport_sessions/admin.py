from django.contrib import admin
from .models import SportSession, SessionExternalAttendee

@admin.register(SessionExternalAttendee)
class SessionExternalAttendeeAdmin(admin.ModelAdmin):
    list_display = ("session", "first_name", "last_name", "note")
    search_fields = ("first_name", "last_name", "note", "session__title")
    list_filter = ("session",)
