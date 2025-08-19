# apps/audit/api/urls.py
from django.urls import path
from .admin_views import AdminAuditExportDeleteView

urlpatterns = [
    path("admin/audit/export/", AdminAuditExportDeleteView.as_view(), name="admin-audit-export"),
    path("admin/audit/", AdminAuditExportDeleteView.as_view(), name="admin-audit-delete"),
]
