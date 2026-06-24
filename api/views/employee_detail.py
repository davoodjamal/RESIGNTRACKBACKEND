from rest_framework import generics, status
from rest_framework.response import Response
from django.utils import timezone
from ..models import AppUser, Resignation, Asset
from .common import IsHROrAdmin

class EmployeeDetailView(generics.RetrieveAPIView):
    queryset = AppUser.objects.all()
    permission_classes = [IsHROrAdmin]

    def retrieve(self, request, *args, **kwargs):
        def get_stars_str(rating):
            if rating is not None and rating != '' and rating != 0:
                try:
                    r = int(rating)
                    if 1 <= r <= 5:
                        return " ".join(['★'] * r + ['☆'] * (5 - r))
                except (ValueError, TypeError):
                    pass
            return 'N/A'

        user = self.get_object()
        
        # Determine status
        status_val = 'Active'
        res = Resignation.objects.filter(email=user.email).order_by('-created_at').first()
        if res:
            if res.status == 'Approved':
                status_val = 'Resigned'
            elif res.status in ['Pending', 'More Info Requested']:
                status_val = 'In-Notice'
            elif res.status in ['Rejected', 'Withdrawn', 'Draft']:
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
            'resignationStatus': res.status if res else None,
            'isEmergencyRequested': (res.exit_feedback.get('emergencyReleaseRequested', False) or res.exit_feedback.get('immediate_release', False)) if (res and isinstance(res.exit_feedback, dict)) else False,
        }

        if res:
            ef = res.exit_feedback if (res.exit_feedback and isinstance(res.exit_feedback, dict)) else {}
            data['initialResignation'] = {
                'reason': res.reason or '',
                'elaboration': res.comments or '',
                'immediateRelease': ef.get('immediate_release', False) or ef.get('emergencyReleaseRequested', False),
                'emergencyReason': ef.get('emergencyReason', ''),
                'emergencyRemarks': ef.get('emergencyRemarks', ''),
                'proposedLastWorkingDay': res.relieving_date.strftime('%Y-%m-%d') if res.relieving_date else '',
                'additionalFeedback': ef.get('additional_feedback', ''),
                'hrRemarks': ef.get('hr_remarks', '')
            }
        else:
            data['initialResignation'] = None

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
            from ..models import ExitInterview
            exit_int = ExitInterview.objects.filter(resignation=res).first()
            if exit_int:
                scaled_rating = exit_int.exit_rating if exit_int.exit_rating is not None else 0.0
                qa_list = [
                    {'question': '1. Primary reason for resignation?', 'answer': exit_int.reason_for_resignation or 'N/A'},
                    {'question': '2. Role & Responsibilities Satisfaction?', 'answer': get_stars_str(exit_int.role_satisfaction)},
                    {'question': '3. Manager Relationship?', 'answer': get_stars_str(exit_int.manager_relationship)},
                    {'question': '4. Career Growth Opportunities?', 'answer': get_stars_str(exit_int.career_growth)},
                    {'question': '5. Company Culture & Environment?', 'answer': get_stars_str(exit_int.company_culture)},
                    {'question': '6. Did you receive adequate training and support?', 'answer': exit_int.adequate_training or 'N/A'},
                    {'question': '7. What did you enjoy most about working here?', 'answer': exit_int.most_enjoyed or 'N/A'},
                    {'question': '8. Suggested improvements for the role or company?', 'answer': exit_int.suggested_improvements or 'N/A'},
                    {'question': '9. RECOMMEND TO OTHERS?', 'answer': exit_int.recommend_to_others or 'N/A'},
                    {'question': '10. CONSIDER REJOINING?', 'answer': exit_int.consider_rejoining or 'N/A'},
                ]
                data['exitInterview'] = {
                    'rating': scaled_rating,
                    'date': exit_int.interview_date.strftime('%Y-%m-%d') if exit_int.interview_date else (exit_int.created_at.date().strftime('%Y-%m-%d') if exit_int.created_at else timezone.now().date().strftime('%Y-%m-%d')),
                    'feedback': exit_int.suggested_improvements or res.comments or 'No feedback provided yet.',
                    'qa': qa_list
                }
            else:
                ef = res.exit_feedback if (res.exit_feedback and isinstance(res.exit_feedback, dict)) else {}
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
                    {'question': '2. Role & Responsibilities Satisfaction?', 'answer': get_stars_str(ef.get('roleRating'))},
                    {'question': '3. Manager Relationship?', 'answer': get_stars_str(ef.get('managerRating'))},
                    {'question': '4. Career Growth Opportunities?', 'answer': get_stars_str(ef.get('growthRating'))},
                    {'question': '5. Company Culture & Environment?', 'answer': get_stars_str(ef.get('cultureRating'))},
                    {'question': '6. Did you receive adequate training and support?', 'answer': 'Yes, absolutely' if ef.get('training') == 'yes' else ('No, it was lacking' if ef.get('training') == 'no' else ef.get('training', 'N/A'))},
                    {'question': '7. What did you enjoy most about working here?', 'answer': ef.get('enjoyText', 'N/A')},
                    {'question': '8. Suggested improvements for the role or company?', 'answer': ef.get('improveText', 'N/A')},
                    {'question': '9. RECOMMEND TO OTHERS?', 'answer': 'Yes' if ef.get('recommend') == 'yes' else ('No' if ef.get('recommend') == 'no' else ef.get('recommend', 'N/A'))},
                    {'question': '10. CONSIDER REJOINING?', 'answer': 'Yes' if ef.get('rejoin') == 'yes' else ('No' if ef.get('rejoin') == 'no' else ef.get('rejoin', 'N/A'))},
                ]
                data['exitInterview'] = {
                    'rating': scaled_rating,
                    'date': res.created_at.date().strftime('%Y-%m-%d') if res.created_at else timezone.now().date().strftime('%Y-%m-%d'),
                    'feedback': ef.get('additional_feedback', res.comments or 'No feedback provided yet.'),
                    'qa': qa_list
                }

            # Tasks/Exit Checklist
            from ..models import ExitChecklistTask
            tasks_qs = ExitChecklistTask.objects.filter(resignation=res)
            data['tasks'] = [
                {'name': t.title, 'status': t.status}
                for t in tasks_qs
            ]

            # Assigned Assets for Notice Status
            data['assets'] = assets_list

            data['remarks'] = res.comments or 'No remarks recorded.'

        elif status_val == 'Resigned':
            # Resigned should contain details, feedback, primary reason
            from ..models import ExitInterview
            exit_int = ExitInterview.objects.filter(resignation=res).first()
            if exit_int:
                scaled_rating = exit_int.exit_rating if exit_int.exit_rating is not None else 0.0
                qa_list = [
                    {'question': '1. Primary reason for resignation?', 'answer': exit_int.reason_for_resignation or 'N/A'},
                    {'question': '2. Role & Responsibilities Satisfaction?', 'answer': get_stars_str(exit_int.role_satisfaction)},
                    {'question': '3. Manager Relationship?', 'answer': get_stars_str(exit_int.manager_relationship)},
                    {'question': '4. Career Growth Opportunities?', 'answer': get_stars_str(exit_int.career_growth)},
                    {'question': '5. Company Culture & Environment?', 'answer': get_stars_str(exit_int.company_culture)},
                    {'question': '6. Did you receive adequate training and support?', 'answer': exit_int.adequate_training or 'N/A'},
                    {'question': '7. What did you enjoy most about working here?', 'answer': exit_int.most_enjoyed or 'N/A'},
                    {'question': '8. Suggested improvements for the role or company?', 'answer': exit_int.suggested_improvements or 'N/A'},
                    {'question': '9. RECOMMEND TO OTHERS?', 'answer': exit_int.recommend_to_others or 'N/A'},
                    {'question': '10. CONSIDER REJOINING?', 'answer': exit_int.consider_rejoining or 'N/A'},
                ]
                data['exitInterview'] = {
                    'rating': scaled_rating,
                    'date': exit_int.interview_date.strftime('%Y-%m-%d') if exit_int.interview_date else (exit_int.created_at.date().strftime('%Y-%m-%d') if exit_int.created_at else timezone.now().date().strftime('%Y-%m-%d')),
                    'feedback': exit_int.suggested_improvements or res.comments or 'No feedback provided.',
                    'qa': qa_list
                }
                data['resignedDate'] = res.relieving_date.strftime('%Y-%m-%d') if res.relieving_date else (res.created_at.date().strftime('%Y-%m-%d') if res.created_at else timezone.now().date().strftime('%Y-%m-%d'))
                data['primaryReason'] = exit_int.reason_for_resignation or 'N/A'
                data['reason'] = exit_int.reason_for_resignation or 'N/A'
            else:
                ef = res.exit_feedback if (res.exit_feedback and isinstance(res.exit_feedback, dict)) else {}
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
                    {'question': '2. Role & Responsibilities Satisfaction?', 'answer': get_stars_str(ef.get('roleRating'))},
                    {'question': '3. Manager Relationship?', 'answer': get_stars_str(ef.get('managerRating'))},
                    {'question': '4. Career Growth Opportunities?', 'answer': get_stars_str(ef.get('growthRating'))},
                    {'question': '5. Company Culture & Environment?', 'answer': get_stars_str(ef.get('cultureRating'))},
                    {'question': '6. Did you receive adequate training and support?', 'answer': 'Yes, absolutely' if ef.get('training') == 'yes' else ('No, it was lacking' if ef.get('training') == 'no' else ef.get('training', 'N/A'))},
                    {'question': '7. What did you enjoy most about working here?', 'answer': ef.get('enjoyText', 'N/A')},
                    {'question': '8. Suggested improvements for the role or company?', 'answer': ef.get('improveText', 'N/A')},
                    {'question': '9. RECOMMEND TO OTHERS?', 'answer': 'Yes' if ef.get('recommend') == 'yes' else ('No' if ef.get('recommend') == 'no' else ef.get('recommend', 'N/A'))},
                    {'question': '10. CONSIDER REJOINING?', 'answer': 'Yes' if ef.get('rejoin') == 'yes' else ('No' if ef.get('rejoin') == 'no' else ef.get('rejoin', 'N/A'))},
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
