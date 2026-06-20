"""
Management command to seed the database with initial data
matching the frontend's hardcoded state.
"""
from django.core.management.base import BaseCommand
from api.models import AppUser, Resignation, SystemSettings, AuditLog
from datetime import date


class Command(BaseCommand):
    help = 'Seed database with initial users, settings, resignations, and audit logs'

    def handle(self, *args, **options):
        # 1. System Settings
        settings = SystemSettings.load()
        self.stdout.write(self.style.SUCCESS(f'✓ SystemSettings ready (notice: {settings.notice_period} days)'))

        # 2. Users
        users_data = [
            {'email': 'employee@resigntrack.com', 'username': 'Alex Mercer', 'role': 'employee', 'password': 'employee123'},
            {'email': 'hr@resigntrack.com', 'username': 'HR Supervisor', 'role': 'hr', 'password': 'hr123'},
            {'email': 'admin@resigntrack.com', 'username': 'Root Administrator', 'role': 'admin', 'password': 'admin123'},
            {'email': 'davood@resigntrack.com', 'username': 'Davood jamal', 'role': 'employee', 'password': 'davood123'},
            {'email': 'amal@resigntrack.com', 'username': 'Amal chavadi', 'role': 'employee', 'password': 'amal123'},
        ]
        for u in users_data:
            AppUser.objects.update_or_create(
                email=u['email'],
                defaults=u
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(users_data)} users seeded'))

        # 3. Sample Resignations
        resignations_data = [
            {
                'email': 'davood@resigntrack.com',
                'name': 'Davood jamal',
                'department': 'Product Design',
                'reason': 'Career Growth',
                'relieving_date': date(2026, 7, 1),
                'comments': 'Loved working here, but found a new product lead role closer to home.',
                'status': 'Approved',
                'exit_feedback': {
                    'cultureRating': 9,
                    'compensationRating': 7,
                    'recommend': 'yes'
                }
            },
            {
                'email': 'amal@resigntrack.com',
                'name': 'Amal chavadi',
                'department': 'DevOps & Security',
                'reason': 'Higher Education',
                'relieving_date': date(2026, 8, 8),
                'comments': 'Pursuing my master degree starting in the Fall term.',
                'status': 'Pending',
                'exit_feedback': {
                    'cultureRating': 8,
                    'compensationRating': 8,
                    'recommend': 'maybe'
                }
            },
        ]
        for r in resignations_data:
            Resignation.objects.update_or_create(
                email=r['email'],
                defaults=r
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(resignations_data)} resignations seeded'))

        # 4. Initial Audit Logs
        if AuditLog.objects.count() == 0:
            AuditLog.objects.create(message='System initiated. Credential profiles loaded.')
            AuditLog.objects.create(message='Standard exit notice period defaults set to 30 days.')
            self.stdout.write(self.style.SUCCESS('✓ 2 audit logs seeded'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ Audit logs already exist, skipping'))

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeding complete!'))
