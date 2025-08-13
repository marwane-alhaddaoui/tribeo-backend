from django.db import models
from .sport_session import SportSession

class SessionExternalAttendee(models.Model):
    session = models.ForeignKey(
        SportSession,
        related_name="external_attendees",
        on_delete=models.CASCADE
    )
    # Snapshot d’un “externe” (à la création/ajout, tu dupliques juste prénom/nom)
    first_name = models.CharField(max_length=120, blank=True)
    last_name  = models.CharField(max_length=120, blank=True)
    note       = models.CharField(max_length=255, blank=True)

    # ✅ nouveau : présence persistée
    present    = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["session", "last_name", "first_name"])]
        unique_together = (("session", "first_name", "last_name"),)

    def __str__(self):
        full = f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
        return f"{full or 'External'} @ {self.session_id}"