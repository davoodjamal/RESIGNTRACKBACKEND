from rest_framework import serializers
from ..models import ExitChecklistTask

class ExitChecklistTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExitChecklistTask
        fields = ['id', 'resignation', 'title', 'description', 'status', 'department', 'due_date', 'completed_at']
        read_only_fields = ['id', 'resignation', 'title', 'description', 'department', 'due_date', 'completed_at']
