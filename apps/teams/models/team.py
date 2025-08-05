from django.db import models
from django.conf import settings
from apps.sport_sessions.models.sport_session import SportSession

class Team(models.Model):
    """
    Équipe appartenant à une session (mode équipe activé).
    """
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, null=True)  # Ex: "Red", "#FF0000"
    session = models.ForeignKey(
        SportSession,
        on_delete=models.CASCADE,
        related_name="teams"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="teams",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams"
        unique_together = ('name', 'session')
        verbose_name = "Équipe"
        verbose_name_plural = "Équipes"

    def __str__(self):
        return f"{self.name} ({self.session.title})"

    def member_count(self):
        return self.members.count()
