# apps/groups/models.py
from django.db import models
from django.conf import settings

# ────────────────────────────────────────────────────────────────────────────────
# Group
# ────────────────────────────────────────────────────────────────────────────────
class Group(models.Model):
    class GroupType(models.TextChoices):
        COACH   = "COACH",  "Coach (invitation uniquement)"
        OPEN    = "OPEN",   "Ouvert (adhésion directe)"
        PRIVATE = "PRIVATE","Privé (demande/validation)"

    name        = models.CharField(max_length=80, unique=True)
    sport       = models.ForeignKey("sports.Sport", on_delete=models.PROTECT, related_name="groups")
    city        = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.URLField(blank=True)

    # NEW: remplace visibility/join_policy par un seul champ sémantique
    group_type  = models.CharField(max_length=10, choices=GroupType.choices, default=GroupType.OPEN)

    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_groups")
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.group_type})"

    # Helpers optionnels (pratiques en vues/permissions)
    @property
    def is_open(self): return self.group_type == self.GroupType.OPEN
    @property
    def is_private(self): return self.group_type == self.GroupType.PRIVATE
    @property
    def is_coach_only(self): return self.group_type == self.GroupType.COACH


# ────────────────────────────────────────────────────────────────────────────────
# GroupMember (on garde ta structure + indexes)
# ────────────────────────────────────────────────────────────────────────────────
class GroupMember(models.Model):
    ROLE_OWNER   = "owner"
    ROLE_MANAGER = "manager"
    ROLE_MEMBER  = "member"
    ROLE_CHOICES = [
        (ROLE_OWNER,   "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_MEMBER,  "Member"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_BANNED = "banned"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_BANNED, "Banned"),
    ]

    group     = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    role      = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    status    = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")
        indexes = [
            models.Index(fields=["group", "user"]),
            models.Index(fields=["status", "role"]),
        ]

    def __str__(self):
        return f"{self.group_id}:{self.user_id}({self.role}/{self.status})"


# ────────────────────────────────────────────────────────────────────────────────
# GroupJoinRequest (pour PRIVATE: demande -> approve/reject par l’owner)
# ────────────────────────────────────────────────────────────────────────────────
class GroupJoinRequest(models.Model):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (PENDING,  "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    group      = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_join_requests")
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")
        indexes = [
            models.Index(fields=["group", "status", "created_at"])
        ]

    def __str__(self):
        return f"JR g={self.group_id} u={self.user_id} [{self.status}]"


# ────────────────────────────────────────────────────────────────────────────────
# GroupExternalMember (membres non-inscrits: prénom/nom, option note)
# ────────────────────────────────────────────────────────────────────────────────
class GroupExternalMember(models.Model):
    group      = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="external_members")
    first_name = models.CharField(max_length=120)
    last_name  = models.CharField(max_length=120)
    note       = models.CharField(max_length=255, blank=True)  # contact, info libre
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["group", "last_name", "first_name"])]

    def __str__(self):
        return f"{self.last_name} {self.first_name} (g={self.group_id})"
