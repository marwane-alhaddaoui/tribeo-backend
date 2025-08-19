# apps/audit/models.py
from django.db import models
from django.conf import settings


class AuditEvent(models.Model):
    """
    Journal d’audit minimal (RGPD-friendly si couplé à utils.audit_log qui anonymise IP/UA).
    NOTE: Ne mets pas d’emails, noms, ou payloads volumineux dans `metadata`.
    """

    when = models.DateTimeField(auto_now_add=True)

    # Pseudonymisation : on ne stocke que l’ID technique de l’utilisateur (FK),
    # sans email/nom. Si l’utilisateur est supprimé, on garde l’évènement (SET_NULL).
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )

    # Action générique: ex. "user.login", "group.create", "session.create"
    verb = models.CharField(max_length=64)

    # Cible de l’action: ex. "SportSession" + "123"
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64, blank=True, default="")

    # IP et User-Agent sont anonymisés/tronqués à l’écriture (voir utils.audit_log)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=128, blank=True, default="")

    # Métadonnées compactes uniquement (ids/status). Aucune donnée sensible ici.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["when"]),
            models.Index(fields=["verb"]),
            models.Index(fields=["object_type", "object_id"]),
        ]
        ordering = ["-when"]

    def __str__(self):
        aid = getattr(self.actor, "id", None)
        return f"{self.when} - {self.verb} (actor={aid})"
