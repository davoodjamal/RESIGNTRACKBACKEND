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


class ResignationFormSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    reason_for_leaving = serializers.CharField(source='reason', required=False, allow_blank=True, allow_null=True)
    elaboration = serializers.CharField(source='comments', required=False, allow_blank=True, allow_null=True)
    last_working_day = serializers.DateField(source='relieving_date', required=False, allow_null=True)
    immediate_release = serializers.BooleanField(write_only=True, required=False)
    emergency_reason = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    emergency_remarks = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    additional_feedback = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Resignation
        fields = [
            'id', 'email', 'name', 'department', 'reason_for_leaving', 'elaboration',
            'last_working_day', 'immediate_release', 'emergency_reason', 'emergency_remarks', 'additional_feedback', 'status'
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Fetch nested fields from exit_feedback JSON
        ef = instance.exit_feedback or {}
        ret['immediate_release'] = ef.get('immediate_release', False)
        ret['emergency_reason'] = ef.get('emergencyReason', '')
        ret['emergency_remarks'] = ef.get('emergencyRemarks', '')
        ret['additional_feedback'] = ef.get('additional_feedback', '')
        ret['hr_remarks'] = ef.get('hr_remarks', '')
        return ret

    def save(self, **kwargs):
        # We need to set default name and department from the logged-in user if creating
        request = self.context.get('request')
        if request and not self.instance:
            self.validated_data['email'] = request.user.email
            self.validated_data['name'] = request.user.full_name or request.user.username or 'Alex Thompson'
            self.validated_data['department'] = request.user.designation or 'Design'

        # Extract immediate_release, additional_feedback, emergency_reason, emergency_remarks to store in exit_feedback
        immediate_release = self.validated_data.pop('immediate_release', False)
        additional_feedback = self.validated_data.pop('additional_feedback', '')
        emergency_reason = self.validated_data.pop('emergency_reason', '')
        emergency_remarks = self.validated_data.pop('emergency_remarks', '')

        # Set exit_feedback structure
        exit_feedback = self.instance.exit_feedback if (self.instance and self.instance.exit_feedback) else {}
        exit_feedback['immediate_release'] = immediate_release
        exit_feedback['additional_feedback'] = additional_feedback
        # Set other defaults for exit interview if not present
        exit_feedback.setdefault('cultureRating', 0)
        exit_feedback.setdefault('compensationRating', 0)
        exit_feedback.setdefault('recommend', 'neutral')
        exit_feedback['emergencyReleaseRequested'] = immediate_release
        exit_feedback['emergencyReason'] = emergency_reason if immediate_release else ''
        exit_feedback['emergencyRemarks'] = emergency_remarks if immediate_release else ''
        
        if 'hr_remarks' in exit_feedback:
            del exit_feedback['hr_remarks']

        self.validated_data['exit_feedback'] = exit_feedback

        return super().save(**kwargs)
