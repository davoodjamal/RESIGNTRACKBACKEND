from rest_framework import serializers
from ..models import Resignation

class ResignationSerializer(serializers.ModelSerializer):
    # Accept camelCase from frontend, map to snake_case model fields
    submissionDate = serializers.DateField(source='submission_date', read_only=True)
    relievingDate = serializers.DateField(source='relieving_date')
    exitFeedback = serializers.JSONField(source='exit_feedback', required=False)

    class Meta:
        model = Resignation
        fields = [
            'id', 'email', 'name', 'department', 'reason',
            'submissionDate', 'relievingDate', 'comments', 'status', 'exitFeedback'
        ]
