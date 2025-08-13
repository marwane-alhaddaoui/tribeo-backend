from django.db import models
from django.conf import settings

class UserMonthlyUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    sessions_created = models.PositiveIntegerField(default=0)
    sessions_joined = models.PositiveIntegerField(default=0)
    groups_joined = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("user", "year", "month"),)

    def __str__(self):
        return f"{self.user_id}-{self.year}-{self.month} c:{self.sessions_created}/j:{self.sessions_joined}/g:{self.groups_joined}"
