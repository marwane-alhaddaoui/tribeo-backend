# apps/audit/api/admin_views.py
from django.http import StreamingHttpResponse, JsonResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework import status
from django.db.models import QuerySet
from django.apps import apps as django_apps
import csv
import io
from datetime import datetime

# --- permission admin déjà dans ton projet ? sinon mini fallback ---
class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and (getattr(u, "is_admin", False) or getattr(u, "is_staff", False) or u.is_superuser))

# --- helper: récupérer le modèle des logs (AuditLog ou AuditEvent) ---
def get_audit_model():
    # Essaie AuditLog, puis AuditEvent (adapté à ton code)
    for model_name in ("AuditLog", "AuditEvent"):
        try:
            return django_apps.get_model("audit", model_name)
        except Exception:
            continue
    raise RuntimeError("Aucun modèle de logs trouvé: audit.AuditLog ou audit.AuditEvent attendu.")

# --- helper: filtre par dates ---
def filter_by_range(qs: QuerySet, request):
    since = request.GET.get("since") or request.data.get("since")
    until = request.GET.get("until") or request.data.get("until")

    # Formats acceptés: YYYY-MM-DD ou ISO8601
    def parse_dt(v):
        if not v:
            return None
        try:
            if len(v) == 10:  # YYYY-MM-DD
                return datetime.fromisoformat(v).replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(v)
        except Exception:
            return None

    since_dt = parse_dt(since)
    until_dt = parse_dt(until)

    # Champ temporel le plus courant
    for date_field in ("created_at", "created", "timestamp", "date_created"):
        if date_field in [f.name for f in qs.model._meta.get_fields()]:
            if since_dt:
                qs = qs.filter(**{f"{date_field}__gte": since_dt})
            if until_dt:
                qs = qs.filter(**{f"{date_field}__lte": until_dt})
            break
    return qs

class AdminAuditExportDeleteView(APIView):
    """
    GET  /api/admin/audit/export/?since=YYYY-MM-DD&until=YYYY-MM-DD
         -> export CSV (Content-Disposition)

    DELETE /api/admin/audit/?since=...&until=...
         -> purge des logs (scope filtré)
    """
    permission_classes = [IsAdminOrStaff]  # remplace par ton IsAdmin si tu l'as

    def get(self, request, *args, **kwargs):
        Audit = get_audit_model()
        qs = Audit.objects.all().order_by("-id")
        qs = filter_by_range(qs, request)

        # Colonnes dynamiques (les plus courantes en tête)
        preferred = ["id", "created_at", "user", "action", "verb", "target_type", "target_id", "ip", "ua", "meta"]
        fields = [f.name for f in Audit._meta.get_fields() if not f.many_to_many and not f.one_to_many]
        # Garder l’ordre: preferred d’abord si présents, puis le reste
        ordered = [f for f in preferred if f in fields] + [f for f in fields if f not in preferred]

        def row_iter():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(ordered)
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)

            BATCH = 1000
            start = 0
            while True:
                chunk = list(qs[start:start+BATCH])
                if not chunk:
                    break
                for obj in chunk:
                    row = []
                    for c in ordered:
                        val = getattr(obj, c, "")
                        # normaliser certains types
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif hasattr(val, "id") and hasattr(val, "__str__"):  # FK user, etc.
                            val = str(val)
                        elif isinstance(val, dict):
                            # compact JSON
                            import json
                            val = json.dumps(val, ensure_ascii=False)
                        row.append(val)
                    writer.writerow(row)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                start += BATCH

        filename = f"audit_logs_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        resp = StreamingHttpResponse(row_iter(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    def delete(self, request, *args, **kwargs):
        Audit = get_audit_model()
        qs = Audit.objects.all()
        qs = filter_by_range(qs, request)

        count = qs.count()
        qs.delete()
        return JsonResponse({"deleted": count}, status=status.HTTP_200_OK)
