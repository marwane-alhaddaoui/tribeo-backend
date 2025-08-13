from django.conf import settings
from django.db import models
from .sport_session import SportSession

class SessionPresence(models.Model):
    session = models.ForeignKey(
        SportSession, on_delete=models.CASCADE, related_name="presences"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="session_presences"
    )
    present = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="presences_marked"
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("session", "user")
