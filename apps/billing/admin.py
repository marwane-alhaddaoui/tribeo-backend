from django.contrib import admin
from .models import BillingProfile, UserMonthlyUsage

@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "stripe_customer_id", "stripe_subscription_id")
    search_fields = ("user__email", "stripe_customer_id", "stripe_subscription_id")
    list_filter = ("plan", "status")

@admin.register(UserMonthlyUsage)
class UserMonthlyUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "year_month", "sessions_created", "groups_created", "participations", "updated_at")
    list_filter = ("year_month",)
    search_fields = ("user__email",)
