# apps/audit/utils.py
from typing import Any, Dict, Optional
import ipaddress

def _client_ip(request) -> Optional[str]:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return (request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_REAL_IP")
            or request.META.get("REMOTE_ADDR"))

def _anonymize_ip_valid(ip: Optional[str]) -> Optional[str]:
    """
    Anonymise en gardant une IP VALIDE:
    - IPv4: /16 -> a.b.0.0
    - IPv6: /64 -> xxxx:xxxx:xxxx:xxxx::
    """
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
        if addr.version == 4:
            net = ipaddress.ip_network(f"{ip}/16", strict=False)
        else:
            net = ipaddress.ip_network(f"{ip}/64", strict=False)
        return str(net.network_address)
    except Exception:
        return None  # si parsing impossible, on ne stocke pas

def _sanitize_user_agent(request) -> str:
    ua = (request.META.get("HTTP_USER_AGENT") or "") if request else ""
    return ua[:50]  # minimisation

def _sanitize_meta(meta: Optional[Dict]) -> Dict:
    if not meta:
        return {}
    # garder seulement des champs techniques courts
    allowed_keys = {"status", "event_type", "member_id", "session_id", "group_id"}
    out = {}
    for k, v in meta.items():
        if k in allowed_keys:
            out[k] = (str(v)[:64] if v is not None else "")
    return out

def audit_log(request, verb: str, obj: Any = None, meta: Optional[Dict] = None, actor=None):
    """
    Écrit un événement d’audit minimal et RGPD-friendly.
    """
    from .models import AuditEvent

    actor = actor or getattr(request, "user", None)
    if actor and not getattr(actor, "is_authenticated", False):
        actor = None

    object_type = obj.__class__.__name__ if obj is not None else ""
    object_id = str(getattr(obj, "pk", "")) if obj is not None else ""

    ip = _anonymize_ip_valid(_client_ip(request))
    ua = _sanitize_user_agent(request)
    meta_small = _sanitize_meta(meta)

    AuditEvent.objects.create(
        actor=actor,
        verb=verb,
        object_type=object_type,
        object_id=object_id,
        ip=ip,               # ex. 127.0.0.0 (anonymisé) au lieu de 127.0.0.1
        user_agent=ua,       # tronqué
        metadata=meta_small, # filtré
    )
