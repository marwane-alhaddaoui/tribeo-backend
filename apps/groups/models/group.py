# apps/groups/models.py
from django.db import models
from django.conf import settings

class Group(models.Model):
    VIS_PUBLIC = "PUBLIC"
    VIS_PRIVATE = "PRIVATE"
    VIS_CHOICES = [(VIS_PUBLIC,"Public"),(VIS_PRIVATE,"Private")]

    POLICY_OPEN = "OPEN"  # V1: on utilise que OPEN
    POLICY_CHOICES = [(POLICY_OPEN,"Open")]

    name = models.CharField(max_length=80, unique=True)
    sport = models.ForeignKey("sports.Sport", on_delete=models.PROTECT, related_name="groups")
    city = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=12, choices=VIS_CHOICES, default=VIS_PUBLIC)
    join_policy = models.CharField(max_length=12, choices=POLICY_CHOICES, default=POLICY_OPEN)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_groups")
    cover_image = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name


class GroupMember(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = [(ROLE_OWNER,"Owner"),(ROLE_MANAGER,"Manager"),(ROLE_MEMBER,"Member")]

    STATUS_ACTIVE = "active"
    STATUS_BANNED = "banned"
    STATUS_CHOICES = [(STATUS_ACTIVE,"Active"),(STATUS_BANNED,"Banned")]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships")
    role  = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    status= models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group","user")
        indexes = [models.Index(fields=["group","user"]), models.Index(fields=["status","role"])]

    def __str__(self):
        return f"{self.group_id}:{self.user_id}({self.role}/{self.status})"
