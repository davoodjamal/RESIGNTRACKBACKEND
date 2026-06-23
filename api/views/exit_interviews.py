from rest_framework import generics, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from ..models import Resignation, Meeting, AppUser
from ..serializers import ResignationSerializer, MeetingSerializer
from .common import IsHROrAdmin

class ExitInterviewListView(generics.ListCreateAPIView):
    """
    GET /api/exit-interviews/ - List all exit interviews with search, filter, sort.
    POST /api/exit-interviews/ - Submit exit interview.
    """
    serializer_class = ResignationSerializer
    permission_classes = [IsHROrAdmin]

    def get_queryset(self):
        queryset = Resignation.objects.exclude(exit_feedback={})
        
        # Search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(department__icontains=search) |
                Q(reason__icontains=search) |
                Q(exit_feedback__reason__icontains=search)
            )
            
        # Exit reason filter
        reason = self.request.query_params.get('reason')
        if reason:
            queryset = queryset.filter(
                Q(reason=reason) | Q(exit_feedback__reason=reason)
            )

        # Department filter
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)
            
        # Sorting
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset


class ExitInterviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Resignation.objects.exclude(exit_feedback={})
    serializer_class = ResignationSerializer
    permission_classes = [IsHROrAdmin]


class LatestExitInterviewView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        latest = Resignation.objects.exclude(exit_feedback={}).order_by('-created_at').first()
        if not latest:
            return Response({}, status=status.HTTP_200_OK)
            
        user = AppUser.objects.filter(email=latest.email).first()
        data = ResignationSerializer(latest).data
        data['employeeId'] = user.id if user else None
        data['designation'] = user.designation if user else 'Employee'
        data['employeeName'] = latest.name
        data['exitDate'] = latest.relieving_date.strftime('%Y-%m-%d') if latest.relieving_date else latest.created_at.date().strftime('%Y-%m-%d')
        data['exitReason'] = latest.exit_feedback.get('reason', latest.reason or 'N/A')
        return Response(data)


class ExitInterviewAnalyticsView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        queryset = Resignation.objects.exclude(exit_feedback={})
        total = queryset.count()
        
        reasons_counts = {}
        for res in queryset:
            reason = res.exit_feedback.get('reason') or res.reason or 'Other'
            reasons_counts[reason] = reasons_counts.get(reason, 0) + 1
            
        sorted_reasons = sorted(reasons_counts.items(), key=lambda x: x[1], reverse=True)
        
        analytics_data = []
        for reason, count in sorted_reasons:
            pct = int((count / total) * 100) if total > 0 else 0
            analytics_data.append({
                'label': reason,
                'count': count,
                'pct': f"{pct}%"
            })
            
        return Response({
            'totalExits': total,
            'reasons': analytics_data
        })


class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all().order_by('-date', '-created_at')
    serializer_class = MeetingSerializer
    permission_classes = [IsHROrAdmin]
