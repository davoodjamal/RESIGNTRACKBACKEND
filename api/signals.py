from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Resignation, ExitChecklistTask

@receiver(post_save, sender=Resignation)
def send_resignation_email_alert(sender, instance, created, **kwargs):
    if created:
        subject = f"Alert: New Resignation Request Submitted - {instance.name}"
        message = (
            f"Dear HR Team,\n\n"
            f"A new resignation request has been filed in the ResignTrack portal.\n\n"
            f"Employee Name: {instance.name}\n"
            f"Email: {instance.email}\n"
            f"Department: {instance.department}\n"
            f"Submission Date: {instance.submission_date}\n"
            f"Proposed Relieving Date: {instance.relieving_date}\n"
            f"Reason: {instance.reason}\n\n"
            f"Comments:\n{instance.comments}\n\n"
            f"Please log in to the portal to review this request.\n\n"
            f"Best regards,\n"
            f"ResignTrack System"
        )
        recipient_list = ['hr@resigntrack.com']
        
        try:
            send_mail(
                subject,
                message,
                'noreply@resigntrack.com',
                recipient_list,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send resignation email alert: {e}")


@receiver(post_save, sender=Resignation)
def create_default_checklist_tasks(sender, instance, created, **kwargs):
    if instance.status in ['Pending', 'Approved']:
        if not instance.checklist_tasks.exists():
            default_tasks = [
                {
                    'title': 'Return Laptop & Accessories',
                    'description': 'IT Department • Confirmed on return',
                    'status': 'Pending',
                    'department': 'IT'
                },
                {
                    'title': 'Complete Handover Documentation',
                    'description': 'Upload final project files and documentation to shared drive.',
                    'status': 'Pending',
                    'department': 'Engineering'
                },
                {
                    'title': 'Revoke Access Cards',
                    'description': 'Return security badge/access card to security desk on final day.',
                    'status': 'Scheduled',
                    'department': 'Security'
                },
                {
                    'title': 'Exit Interview Feedback Form',
                    'description': 'Complete exit survey before your final day.',
                    'status': 'Pending',
                    'department': 'HR'
                },
                {
                    'title': 'Clear Financial Dues',
                    'description': 'Settle outstanding expenses, advances, and verify final payroll.',
                    'status': 'Pending',
                    'department': 'Finance'
                },
                {
                    'title': 'Deactivate Corporate Accounts',
                    'description': 'Revoke corporate email, Slack, and cloud service access.',
                    'status': 'Pending',
                    'department': 'IT'
                }
            ]
            for task in default_tasks:
                ExitChecklistTask.objects.create(
                    resignation=instance,
                    title=task['title'],
                    description=task['description'],
                    status=task['status'],
                    department=task['department']
                )
