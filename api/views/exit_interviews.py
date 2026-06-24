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

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsHROrAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Meeting.objects.none()
        if user.role in ['hr', 'admin']:
            return Meeting.objects.all().order_by('-date', '-created_at')
        return Meeting.objects.filter(employee=user).order_by('-date', '-created_at')

    def perform_create(self, serializer):
        meeting = serializer.save()
        employee = meeting.employee
        hr_email = "amal@resigntrack.com"
        employee_email = employee.email
        
        # Stub notification/calendar invite logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Triggering email/calendar invitation to HR ({hr_email}) and Employee ({employee_email}) for Jitsi meeting: {meeting.jitsi_url}")
        
        # System notification for the employee
        from .notification import create_notification
        create_notification(
            user=employee,
            title="Exit Consultation Scheduled",
            message=f"Your exit consultation meeting has been scheduled for {meeting.date} at {meeting.time_slot}. Join Jitsi room: {meeting.jitsi_url}",
            icon="video_call"
        )


class ExitInterviewSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from django.utils import timezone
        from ..models import ExitInterview, Resignation
        data = request.data
        
        # Mappings from frontend style to our schema
        resignation_id = data.get('resignation_id') or data.get('resignation')
        status_val = data.get('status', 'DRAFT').upper()
        
        reason = data.get('reason_for_resignation') or data.get('reason', '')
        
        role_satisfaction = data.get('role_satisfaction') or data.get('roleRating')
        manager_relationship = data.get('manager_relationship') or data.get('managerRating')
        career_growth = data.get('career_growth') or data.get('growthRating')
        company_culture = data.get('company_culture') or data.get('cultureRating')
        
        training_raw = data.get('adequate_training') or data.get('training', '')
        if training_raw in ['yes', 'Yes, absolutely']:
            adequate_training = 'Yes, absolutely'
        elif training_raw in ['no', 'No, it was lacking']:
            adequate_training = 'No, it was lacking'
        else:
            adequate_training = training_raw
            
        most_enjoyed = data.get('most_enjoyed') or data.get('enjoyText', '')
        suggested_improvements = data.get('suggested_improvements') or data.get('improveText', '')
        
        rec_raw = data.get('recommend_to_others') or data.get('recommend', '')
        if rec_raw in ['yes', 'Yes']:
            recommend_to_others = 'Yes'
        elif rec_raw in ['no', 'No']:
            recommend_to_others = 'No'
        else:
            recommend_to_others = rec_raw
            
        rej_raw = data.get('consider_rejoining') or data.get('rejoin', '')
        if rej_raw in ['yes', 'Yes']:
            consider_rejoining = 'Yes'
        elif rej_raw in ['no', 'No']:
            consider_rejoining = 'No'
        else:
            consider_rejoining = rej_raw

        # Strict validation
        for val, name in [
            (role_satisfaction, 'role_satisfaction'),
            (manager_relationship, 'manager_relationship'),
            (career_growth, 'career_growth'),
            (company_culture, 'company_culture')
        ]:
            if val is not None and val != 0 and val != '':
                try:
                    int_val = int(val)
                    if int_val < 1 or int_val > 5:
                        return Response({"error": f"{name} must strictly be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, TypeError):
                    return Response({"error": f"{name} must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Get resignation
        if resignation_id:
            res_obj = Resignation.objects.filter(id=resignation_id).first()
        else:
            res_obj = Resignation.objects.filter(email=request.user.email).order_by('-created_at').first()

        if not res_obj:
            return Response({"error": "No active resignation found."}, status=status.HTTP_400_BAD_REQUEST)

        # Helper to compute employee_id_code
        hash_val = request.user.id
        years = [2019, 2020, 2021, 2022, 2023]
        year = years[hash_val % len(years)]
        employee_id_code = f"EF-{year}-{request.user.id:04d}"

        # Calculate exit_rating if status is SUBMITTED
        exit_rating = None
        if status_val == 'SUBMITTED':
            ratings = [role_satisfaction, manager_relationship, career_growth, company_culture]
            valid_ratings = []
            for r in ratings:
                if r is not None and r != '' and r != 0:
                    try:
                        valid_ratings.append(int(r))
                    except (ValueError, TypeError):
                        pass
            if valid_ratings:
                avg = sum(valid_ratings) / len(valid_ratings)
                exit_rating = round(avg * 2.0, 1)
            else:
                exit_rating = 0.0

        # Save/Update ExitInterview
        interview, created = ExitInterview.objects.get_or_create(
            employee=request.user,
            resignation=res_obj
        )
        interview.employee_id_code = employee_id_code
        interview.employee_name = request.user.full_name or request.user.username
        interview.last_working_day = res_obj.relieving_date
        
        if status_val == 'SUBMITTED':
            interview.interview_date = timezone.now().date()
            interview.exit_rating = exit_rating
        
        interview.status = status_val
        interview.reason_for_resignation = reason
        if role_satisfaction is not None and role_satisfaction != '':
            interview.role_satisfaction = int(role_satisfaction)
        if manager_relationship is not None and manager_relationship != '':
            interview.manager_relationship = int(manager_relationship)
        if career_growth is not None and career_growth != '':
            interview.career_growth = int(career_growth)
        if company_culture is not None and company_culture != '':
            interview.company_culture = int(company_culture)
            
        interview.adequate_training = adequate_training
        interview.most_enjoyed = most_enjoyed
        interview.suggested_improvements = suggested_improvements
        interview.recommend_to_others = recommend_to_others
        interview.consider_rejoining = consider_rejoining
        interview.save()

        # Update exit_feedback on Resignation for compatibility with other views
        exit_feedback = res_obj.exit_feedback if (res_obj.exit_feedback and isinstance(res_obj.exit_feedback, dict)) else {}
        exit_feedback.update({
            'reason': reason,
            'roleRating': int(role_satisfaction) if (role_satisfaction is not None and role_satisfaction != '') else 0,
            'managerRating': int(manager_relationship) if (manager_relationship is not None and manager_relationship != '') else 0,
            'growthRating': int(career_growth) if (career_growth is not None and career_growth != '') else 0,
            'cultureRating': int(company_culture) if (company_culture is not None and company_culture != '') else 0,
            'training': 'yes' if adequate_training == 'Yes, absolutely' else 'no',
            'enjoyText': most_enjoyed,
            'improveText': suggested_improvements,
            'recommend': 'yes' if recommend_to_others == 'Yes' else 'no',
            'rejoin': 'yes' if consider_rejoining == 'Yes' else 'no',
            'additional_feedback': suggested_improvements,
        })
        res_obj.exit_feedback = exit_feedback
        res_obj.save()

        # If status is SUBMITTED, update ExitChecklistTask and Resignation status
        if status_val == 'SUBMITTED':
            res_obj.status = 'Pending'
            res_obj.save()
            from ..models import ExitChecklistTask
            ExitChecklistTask.objects.filter(
                resignation=res_obj,
                title__iexact='Exit Interview'
            ).update(
                status='Completed',
                completed_at=timezone.now()
            )

        return Response({
            "success": True,
            "message": "Exit interview saved successfully.",
            "data": {
                "id": interview.id,
                "status": interview.status,
                "exit_rating": interview.exit_rating
            }
        }, status=status.HTTP_200_OK)


class HREmployeeExitInterviewView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, id, *args, **kwargs):
        from ..models import ExitInterview
        employee_user = AppUser.objects.filter(id=id).first()
        if not employee_user:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get latest resignation
        res_obj = Resignation.objects.filter(email=employee_user.email).order_by('-created_at').first()
        if not res_obj:
            return Response({"error": "No resignation found for this employee."}, status=status.HTTP_404_NOT_FOUND)

        # Find ExitInterview
        interview = ExitInterview.objects.filter(resignation=res_obj).first()
        if not interview:
            return Response({"error": "No exit interview found for this employee."}, status=status.HTTP_404_NOT_FOUND)

        def get_stars_str(rating):
            if rating is not None and rating != '' and rating != 0:
                try:
                    r = int(rating)
                    if 1 <= r <= 5:
                        return " ".join(['★'] * r + ['☆'] * (5 - r))
                except (ValueError, TypeError):
                    pass
            return 'N/A'

        rating_str = f"{int(interview.exit_rating)}/10" if interview.exit_rating is not None else "0/10"
        
        qa_list = [
            {'question': '1. Primary reason for resignation?', 'answer': interview.reason_for_resignation or 'N/A'},
            {'question': '2. Role & Responsibilities Satisfaction?', 'answer': get_stars_str(interview.role_satisfaction)},
            {'question': '3. Manager Relationship?', 'answer': get_stars_str(interview.manager_relationship)},
            {'question': '4. Career Growth Opportunities?', 'answer': get_stars_str(interview.career_growth)},
            {'question': '5. Company Culture & Environment?', 'answer': get_stars_str(interview.company_culture)},
            {'question': '6. Did you receive adequate training and support?', 'answer': interview.adequate_training or 'N/A'},
            {'question': '7. What did you enjoy most about working here?', 'answer': interview.most_enjoyed or 'N/A'},
            {'question': '8. Suggested improvements for the role or company?', 'answer': interview.suggested_improvements or 'N/A'},
            {'question': '9. RECOMMEND TO OTHERS?', 'answer': interview.recommend_to_others or 'N/A'},
            {'question': '10. CONSIDER REJOINING?', 'answer': interview.consider_rejoining or 'N/A'},
        ]

        return Response({
            "employee_id": interview.employee_id_code,
            "employee_name": interview.employee_name,
            "last_working_day": interview.last_working_day.strftime('%Y-%m-%d') if interview.last_working_day else '',
            "interview_date": interview.interview_date.strftime('%Y-%m-%d') if interview.interview_date else '',
            "exit_rating": rating_str,
            "status": interview.status,
            "remarks_and_reason": interview.suggested_improvements or 'No feedback provided yet.',
            "responses": qa_list,
            "qa": qa_list
        }, status=status.HTTP_200_OK)

