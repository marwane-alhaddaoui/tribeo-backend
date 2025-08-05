from django.db import models
from django.conf import settings

class SportSession(models.Model):
    SPORT_CHOICES = [
        ('football', 'Football'),
        ('basketball', 'Basketball'),
        ('running', 'Running'),
        ('cycling', 'Cycling'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=100)
    sport = models.CharField(max_length=50, choices=SPORT_CHOICES)
    location = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    max_participants = models.PositiveIntegerField(default=10)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_sessions'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='joined_sessions',
        blank=True
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sport_session'  # 👈 nom clair dans la base

    def is_full(self):
        return self.participants.count() >= self.max_participants

    def __str__(self):
        return f"{self.title} - {self.sport} ({self.date})"
