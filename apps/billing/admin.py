from django.contrib import admin
from .models import UserMonthlyUsage

@admin.register(UserMonthlyUsage)
class UserMonthlyUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "month", "sessions_created", "sessions_joined", "groups_joined")
    search_fields = ("user__email", "user__username")
    list_filter = ("year", "month")
