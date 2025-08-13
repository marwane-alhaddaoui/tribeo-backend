from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.sport_sessions.models import (
    SportSession,
    SessionPresence,
    SessionExternalAttendee,
)
from apps.groups.models import GroupMember  # ✅ pour fallback membres de groupe

User = get_user_model()


def _can_manage(request_user, session: SportSession) -> bool:
    """Créateur OK + éventuel owner/manager du groupe."""
    if getattr(session, "creator_id", None) == getattr(request_user, "id", None):
        return True
    if getattr(session, "group", None) and hasattr(session.group, "is_owner_or_manager_for"):
        try:
            return bool(session.group.is_owner_or_manager_for(request_user))
        except TypeError:
            return False
    return False


class SessionAttendanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk: int, *args, **kwargs):
        """
        Retourne l’assiduité (internes + externes).
        Source internes:
          1) session.participants
          2) fallback: membres ACTIFS du groupe (si aucun participant lié)
        Exclut coach/creator. Inclut externes (SessionExternalAttendee).
        Compat FE: 'attendees' et 'attendance'.
        """
        session = get_object_or_404(SportSession, pk=pk)

        # --- Exclusions pour internes ---
        exclude_ids = set()
        if getattr(session, "creator_id", None):
            exclude_ids.add(int(session.creator_id))
        try:
            coach_id = getattr(getattr(session, "group", None), "coach_id", None)
            if coach_id:
                exclude_ids.add(int(coach_id))
        except Exception:
            coach_id = None

        # --- Map des présences internes ---
        presences = SessionPresence.objects.filter(session=session).only("user_id", "present")
        presence_map = {p.user_id: bool(p.present) for p in presences}

        # --- Internes (source de vérité + fallback) ---
        # 1) participants liés à la session
        qs_users = session.participants.all()

        # 2) fallback sur membres du groupe si vide
        if not qs_users.exists() and session.group_id:
            # Membres actifs du groupe (owner + memberships STATUS_ACTIVE)
            ids = []

            # owner
            if getattr(session.group, "owner_id", None):
                ids.append(session.group.owner_id)

            # memberships actifs
            active_qs = session.group.memberships.select_related("user").filter(
                status=GroupMember.STATUS_ACTIVE
            )
            for gm in active_qs:
                if gm.user_id and gm.user_id not in ids:
                    ids.append(gm.user_id)

            # construire queryset Users sur ces ids
            if ids:
                qs_users = User.objects.filter(id__in=ids)

        # filtres d’exclusion
        if exclude_ids:
            qs_users = qs_users.exclude(id__in=list(exclude_ids))
        # essayer d’exclure par rôle global si dispo
        try:
            qs_users = qs_users.exclude(role__iexact="coach")
        except Exception:
            pass

        participants = list(qs_users.values("id", "username", "email", "role"))

        # payload internes
        data = [
            {
                "user_id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "role": u.get("role"),
                "present": presence_map.get(u["id"], False),
                "external": False,
            }
            for u in participants
        ]

        # utilisateurs “hors groupe/participants” mais avec présence (rare)
        participant_ids = {u["id"] for u in participants}
        for uid, is_present in presence_map.items():
            if uid in participant_ids or uid in exclude_ids:
                continue
            data.append({
                "user_id": uid,
                "username": None,
                "email": None,
                "role": None,
                "present": is_present,
                "external": True,  # user hors groupe
            })

        # --- Externes (SessionExternalAttendee) ---
        for em in SessionExternalAttendee.objects.filter(session=session).only(
            "id", "first_name", "last_name", "note", "present"
        ).order_by("id"):
            data.append(
                {
                    "external_attendee_id": em.id,
                    "first_name": em.first_name,
                    "last_name": em.last_name,
                    "note": em.note,
                    "present": bool(em.present),
                    "external": True,
                    "read_only": False,
                }
            )

        payload = {
            "session_id": session.id,
            "attendees": data,
            "attendance": data,
        }
        return Response(payload, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request, pk: int, *args, **kwargs):
        """
        Upsert:
        - Internes: { user_id, present, note? }
        - Externes: { external_attendee_id, present, note? }
        Compat: 'attendees' ou 'attendance'
        """
        session = get_object_or_404(SportSession, pk=pk)

        if not _can_manage(request.user, session):
            return Response({"detail": "Vous n'avez pas les droits."}, status=status.HTTP_403_FORBIDDEN)

        attendees = request.data.get("attendees")
        if attendees is None:
            attendees = request.data.get("attendance")
        if not isinstance(attendees, list):
            return Response({"detail": "attendees/attendance doit être une liste."}, status=status.HTTP_400_BAD_REQUEST)

        updated = []

        for item in attendees:
            # --- Externe ---
            if item.get("external_attendee_id") is not None:
                try:
                    ext_id = int(item.get("external_attendee_id"))
                except (TypeError, ValueError):
                    continue
                present = bool(item.get("present", False))
                note = (item.get("note") or "").strip()

                try:
                    em = SessionExternalAttendee.objects.select_for_update().get(id=ext_id, session=session)
                except SessionExternalAttendee.DoesNotExist:
                    continue

                changed = False
                if bool(em.present) != present:
                    em.present = present
                    changed = True
                if (em.note or "") != note:
                    em.note = note
                    changed = True
                if changed:
                    em.save()

                updated.append({
                    "external_attendee_id": em.id,
                    "present": em.present,
                    "note": em.note,
                })
                continue

            # --- Interne ---
            if item.get("user_id") is not None:
                try:
                    uid = int(item.get("user_id"))
                except (TypeError, ValueError):
                    continue

                present = bool(item.get("present", False))
                note = (item.get("note") or "").strip()

                # Exclure coach/creator
                if getattr(session, "creator_id", None) == uid:
                    continue
                grp_coach_id = getattr(getattr(session, "group", None), "coach_id", None)
                if grp_coach_id and int(grp_coach_id) == uid:
                    continue

                obj, created = SessionPresence.objects.get_or_create(
                    session=session,
                    user_id=uid,
                    defaults={"present": present, "note": note},
                )
                if not created:
                    changed = False
                    if obj.present != present:
                        obj.present = present
                        changed = True
                    if (obj.note or "") != note:
                        obj.note = note
                        changed = True
                    if changed:
                        obj.save()

                updated.append({
                    "user_id": obj.user_id,
                    "present": obj.present,
                    "note": obj.note,
                })
                continue

            # ni user_id ni external_attendee_id → ignore
            continue

        return Response({"updated": updated, "attendance": updated, "attendees": updated}, status=status.HTTP_200_OK)
