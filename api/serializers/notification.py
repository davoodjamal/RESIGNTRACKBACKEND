from rest_framework import serializers
from ..models import Notification, Announcement

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'icon', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'icon', 'created_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'expiry', 'expiry_time', 'created_at']
        read_only_fields = ['id', 'created_at']

