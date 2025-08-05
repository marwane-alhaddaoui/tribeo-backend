from django.db import models
from django.conf import settings

class Group(models.Model):
    """
    Groupe de joueurs géré par un coach ou un admin.
    Utilisé pour organiser des sessions et tournois.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_groups"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="joined_groups",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "groups"
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"

    def __str__(self):
        return self.name

    def member_count(self):
        return self.members.count()
