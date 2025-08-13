# apps/chat/models/chat_message.py
from django.db import models
from django.conf import settings

class ChatMessage(models.Model):
    """
    Message posté soit dans un Groupe, soit dans une Session (XOR).
    """
    group   = models.ForeignKey(
        'groups.Group', null=True, blank=True,
        on_delete=models.CASCADE, related_name='chat_messages'
    )
    session = models.ForeignKey(
        'sport_sessions.SportSession', null=True, blank=True,
        on_delete=models.CASCADE, related_name='chat_messages'
    )

    sender  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_chat_messages'
    )
    content = models.TextField()

    # Modération / soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='chat_deletions'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'created_at']),
            models.Index(fields=['session', 'created_at']),
        ]

    def clean(self):
        # XOR strict: exactement un des deux doit être renseigné
        if bool(self.group) == bool(self.session):
            from django.core.exceptions import ValidationError
            raise ValidationError('Provide group XOR session for ChatMessage.')

    def __str__(self):
        target = f'group={self.group_id}' if self.group_id else f'session={self.session_id}'
        return f'<ChatMessage {self.id} {target} sender={self.sender_id} deleted={self.is_deleted}>'
