# apps/chat/api/serializers/chat_message_serializer.py
from rest_framework import serializers
from django.utils.timesince import timesince
from apps.chat.models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    mine = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    created_ago = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender_username', 'content',
            'is_deleted', 'created_at', 'created_ago',
            'mine', 'can_delete'
        ]

    def get_mine(self, obj):
        req = self.context.get('request')
        user = getattr(req, 'user', None)
        return bool(user and user.is_authenticated and obj.sender_id == user.id)

    def get_can_delete(self, obj):
        """La vue fournit context['can_delete_cb'] = lambda user, obj: bool"""
        cb = self.context.get('can_delete_cb')
        req = self.context.get('request')
        user = getattr(req, 'user', None)
        if not callable(cb) or not user or not user.is_authenticated:
            return False
        return bool(cb(user, obj))

    def get_created_ago(self, obj):
        return timesince(obj.created_at) + ' ago'
