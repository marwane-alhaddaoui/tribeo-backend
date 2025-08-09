from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Group(models.Model):
    name = models.CharField(max_length=120)
    sport = models.ForeignKey('sports.Sport', on_delete=models.PROTECT, related_name='groups', null=True, blank=True)
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coached_groups')
    members = models.ManyToManyField(User, related_name='member_groups', blank=True)
    is_private = models.BooleanField(default=False)
    description = models.TextField(blank=True)  # (ou blank=True, null=True si tu as choisi Option B)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        role = getattr(self.coach, 'role', None)
        if role not in ('coach', 'admin'):
            raise ValidationError("Le coach du groupe doit avoir le rôle 'coach' ou 'admin'.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.members.add(self.coach)  # coach auto-membre
