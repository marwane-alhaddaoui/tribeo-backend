from django.db import models
from django.conf import settings

class BillingProfile(models.Model):
    PLAN_FREE = "free"
    PLAN_PREMIUM = "premium"
    PLAN_COACH = "coach"
    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PREMIUM, "Premium"),
        (PLAN_COACH, "Coach"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing")
    stripe_customer_id = models.CharField(max_length=64, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=64, blank=True, null=True)
    plan = models.CharField(max_length=16, choices=PLAN_CHOICES, default=PLAN_FREE)
    status = models.CharField(max_length=32, default="inactive")
    cancel_at = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} · {self.plan} · {self.status}"


class UserMonthlyUsage(models.Model):
    """
    Compteurs mensuels par utilisateur pour appliquer les quotas.
    year_month = 'YYYY-MM' (ex: '2025-08')
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monthly_usage")
    year_month = models.CharField(max_length=7)  # 'YYYY-MM'
    sessions_created = models.PositiveIntegerField(default=0)
    groups_created = models.PositiveIntegerField(default=0)
    participations = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    trainings_created = models.IntegerField(default=0)
    class Meta:
        unique_together = ("user", "year_month")

    def __str__(self):
        return f"{self.user} · {self.year_month}"
