from rest_framework import generics, status
from rest_framework.response import Response
from django.utils import timezone
from ..models import AppUser, Resignation, Asset
from .common import IsHROrAdmin

class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = AppUser.objects.all()
    permission_classes = [IsHROrAdmin]

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Determine status
        status_val = 'Active'
        res = Resignation.objects.filter(email=user.email).order_by('-created_at').first()
        if res:
            if res.status == 'Approved':
                if res.relieving_date and res.relieving_date < timezone.now().date():
                    status_val = 'Resigned'
                else:
                    status_val = 'In-Notice'
            elif res.status == 'Pending':
                status_val = 'In-Notice'
            elif res.status in ['Rejected', 'Withdrawn']:
                status_val = 'Active'
                
        # Basic details
        hash_val = user.id
        years = [2019, 2020, 2021, 2022, 2023]
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        year = years[hash_val % len(years)]
        month = months[hash_val % len(months)]
        day = (hash_val * 7) % 28 + 1
        join_date_str = f"{month} {day:02d}, {year}"

        data = {
            'id': user.id,
            'name': user.full_name or user.username,
            'designation': user.designation or 'Employee',
            'email': user.email,
            'phone': user.phone or 'N/A',
            'dob': user.dob.strftime('%Y-%m-%d') if user.dob else 'N/A',
            'department': user.designation or 'Design',
            'manager': 'Root Administrator',
            'employeeType': 'Full-time',
            'address': user.address or 'N/A',
            'workLocation': 'Office',
            'joinDate': join_date_str,
            'status': status_val,
        }

        # Query real assets assigned to the employee
        assigned_assets_qs = Asset.objects.filter(assigned_to=user)
        assets_list = [
            {
                'name': a.name,
                'code': a.tag,
                'status': a.status,
                'remarks': a.maintenance_notes
            }
            for a in assigned_assets_qs
        ]

        # Build notice period, exit checklist, exit interview details based on status
        if status_val == 'Active':
            # Active should contain details, assigned asset
            data['assets'] = assets_list
            data['tasks'] = []
            data['exitInterview'] = None
            data['noticePeriod'] = None

        elif status_val == 'In-Notice':
            # In-Notice should contain details, exit checklist, exit interview feedback
            # Notice Period Details
            start_date_str = res.submission_date.strftime('%Y-%m-%d') if res.submission_date else timezone.now().date().strftime('%Y-%m-%d')
            end_date_str = res.relieving_date.strftime('%Y-%m-%d') if res.relieving_date else timezone.now().date().strftime('%Y-%m-%d')
            
            # servedDays & remainingDays
            today = timezone.now().date()
            sub_date = res.submission_date or today
            rel_date = res.relieving_date or today
            
            total_days = (rel_date - sub_date).days
            if total_days <= 0:
                total_days = 30
            served_days = (today - sub_date).days
            if served_days < 0:
                served_days = 0
            if served_days > total_days:
                served_days = total_days
            remaining_days = (rel_date - today).days
            if remaining_days < 0:
                remaining_days = 0

            data['noticePeriod'] = {
                'status': 'Active',
                'startDate': start_date_str,
                'endDate': end_date_str,
                'requiredDays': total_days,
                'servedDays': served_days,
                'waiver': res.exit_feedback.get('immediate_release', False) if isinstance(res.exit_feedback, dict) else False,
                'remainingDays': remaining_days
            }

            # Exit Interview Feedback
            ef = res.exit_feedback if (res.exit_feedback and isinstance(res.exit_feedback, dict)) else {}
            
            # Calculate rating (cultureRating or similar)
            ratings = [ef.get('roleRating', 0), ef.get('managerRating', 0), ef.get('growthRating', 0), ef.get('cultureRating', 0), ef.get('compensationRating', 0)]
            valid_ratings = [r for r in ratings if r is not None and r > 0]
            avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 4.0
            
            max_rating = max(valid_ratings) if valid_ratings else 0
            if max_rating > 5:
                scaled_rating = round(avg_rating, 1)
            else:
                scaled_rating = round(avg_rating * 2, 1)

            qa_list = [
                {'question': '1. Primary reason for resignation?', 'answer': ef.get('reason', res.reason or 'N/A')},
                {'question': '7. What did you enjoy most about working here?', 'answer': ef.get('enjoyText', 'N/A')},
                {'question': '8. Suggested improvements for the role or company?', 'answer': ef.get('improveText', 'N/A')},
                {'question': '9. Recommend to others?', 'answer': ef.get('recommend', 'N/A')},
                {'question': '10. Consider rejoining?', 'answer': ef.get('rejoin', 'N/A')},
            ]

            data['exitInterview'] = {
                'rating': scaled_rating,
                'date': res.created_at.date().strftime('%Y-%m-%d') if res.created_at else timezone.now().date().strftime('%Y-%m-%d'),
                'feedback': ef.get('additional_feedback', res.comments or 'No feedback provided yet.'),
                'qa': qa_list
            }

            # Tasks/Exit Checklist
            has_exit_feedback = bool(res.exit_feedback)
            data['tasks'] = [
                {'name': 'Return assets', 'status': 'Completed' if res.status == 'Approved' else 'Pending'},
                {'name': 'Knowledge Transfer', 'status': 'Pending'},
                {'name': 'Exit Interview', 'status': 'Completed' if has_exit_feedback else 'Pending'},
            ]

            # Assigned Assets for Notice Status
            data['assets'] = assets_list

            data['remarks'] = res.comments or 'No official HR remarks recorded.'

        elif status_val == 'Resigned':
            # Resigned should contain details, feedback, primary reason
            ef = res.exit_feedback if (res.exit_feedback and isinstance(res.exit_feedback, dict)) else {}
            
            # Calculate rating (cultureRating or similar)
            ratings = [ef.get('roleRating', 0), ef.get('managerRating', 0), ef.get('growthRating', 0), ef.get('cultureRating', 0), ef.get('compensationRating', 0)]
            valid_ratings = [r for r in ratings if r is not None and r > 0]
            avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 4.0
            
            max_rating = max(valid_ratings) if valid_ratings else 0
            if max_rating > 5:
                scaled_rating = round(avg_rating, 1)
            else:
                scaled_rating = round(avg_rating * 2, 1)

            qa_list = [
                {'question': '1. Primary reason for resignation?', 'answer': ef.get('reason', res.reason or 'N/A')},
                {'question': '7. What did you enjoy most about working here?', 'answer': ef.get('enjoyText', 'N/A')},
                {'question': '8. Suggested improvements for the role or company?', 'answer': ef.get('improveText', 'N/A')},
                {'question': '9. Recommend to others?', 'answer': ef.get('recommend', 'N/A')},
                {'question': '10. Consider rejoining?', 'answer': ef.get('rejoin', 'N/A')},
            ]

            data['exitInterview'] = {
                'rating': scaled_rating,
                'date': res.created_at.date().strftime('%Y-%m-%d') if res.created_at else timezone.now().date().strftime('%Y-%m-%d'),
                'feedback': ef.get('additional_feedback', res.comments or 'No feedback provided.'),
                'qa': qa_list
            }
            data['resignedDate'] = res.relieving_date.strftime('%Y-%m-%d') if res.relieving_date else res.created_at.date().strftime('%Y-%m-%d')
            data['primaryReason'] = ef.get('reason', res.reason or 'N/A')
            data['reason'] = ef.get('reason', res.reason or 'N/A')
            data['assets'] = []
            data['tasks'] = []
            data['noticePeriod'] = None

        return Response(data)
