from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Resignation, ExitChecklistTask, RescheduleRequest, AppUser, Notification

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


@receiver(post_save, sender=Resignation)
def notify_resignation_changes(sender, instance, created, **kwargs):
    # Get all HR and Admin users to notify
    hr_admins = AppUser.objects.filter(role__in=['hr', 'admin'])
    employee = AppUser.objects.filter(email=instance.email).first()

    if created and instance.status == 'Pending':
        # Notify HR & Admins
        for hr_admin in hr_admins:
            Notification.objects.create(
                user=hr_admin,
                title="New Resignation Submitted",
                message=f"{instance.name} has submitted a resignation request.",
                icon="assignment"
            )
        # Notify Employee
        if employee:
            Notification.objects.create(
                user=employee,
                title="Resignation Submitted",
                message="Your resignation request has been successfully submitted and is under review.",
                icon="assignment"
            )
    elif not created:
        if instance.status == 'Pending':
            # Check if we already sent submission notification (e.g. from draft submission transition)
            if employee:
                exists = Notification.objects.filter(
                    user=employee,
                    title="Resignation Submitted"
                ).exists()
                if not exists:
                    # Notify HR & Admins
                    for hr_admin in hr_admins:
                        Notification.objects.create(
                            user=hr_admin,
                            title="New Resignation Submitted",
                            message=f"{instance.name} has submitted a resignation request.",
                            icon="assignment"
                        )
                    # Notify Employee
                    Notification.objects.create(
                        user=employee,
                        title="Resignation Submitted",
                        message="Your resignation request has been successfully submitted and is under review.",
                        icon="assignment"
                    )
        elif instance.status == 'Approved':
            if employee:
                # 1. Notify Resignation Approval
                Notification.objects.get_or_create(
                    user=employee,
                    title="Resignation Approved",
                    message="Your resignation request has been approved by HR.",
                    icon="thumb_up"
                )
                # 2. Notify Exit Interview Scheduled
                Notification.objects.get_or_create(
                    user=employee,
                    title="Exit Interview Scheduled",
                    message=f"Your exit interview is scheduled for {instance.meeting_schedule}.",
                    icon="calendar_month"
                )
                # 3. Notify Checklist Generated
                Notification.objects.get_or_create(
                    user=employee,
                    title="Exit Checklist Generated",
                    message="Your offboarding checklist has been generated. Please complete your tasks.",
                    icon="fact_check"
                )
        elif instance.status == 'Rejected':
            if employee:
                Notification.objects.get_or_create(
                    user=employee,
                    title="Resignation Rejected",
                    message="Your resignation request has been rejected by HR.",
                    icon="warning"
                )
        elif instance.status == 'Withdrawn':
            # Notify HR & Admins
            for hr_admin in hr_admins:
                Notification.objects.create(
                    user=hr_admin,
                    title="Resignation Withdrawn",
                    message=f"{instance.name} has withdrawn their resignation request.",
                    icon="cancel"
                )
            # Notify Employee
            if employee:
                Notification.objects.create(
                    user=employee,
                    title="Resignation Withdrawn",
                    message="You have successfully withdrawn your resignation request.",
                    icon="cancel"
                )



@receiver(post_save, sender=RescheduleRequest)
def notify_reschedule_request_changes(sender, instance, created, **kwargs):
    hr_admins = AppUser.objects.filter(role__in=['hr', 'admin'])
    employee = AppUser.objects.filter(email=instance.resignation.email).first()

    if created:
        # Notify HR & Admins
        for hr_admin in hr_admins:
            Notification.objects.create(
                user=hr_admin,
                title="Reschedule Requested",
                message=f"{instance.resignation.name} requested to reschedule exit interview to {instance.requested_date} at {instance.requested_time}.",
                icon="calendar_month"
            )
    else:
        if instance.status == 'Approved':
            if employee:
                Notification.objects.create(
                    user=employee,
                    title="Reschedule Approved",
                    message=f"Your exit interview reschedule request has been approved: {instance.requested_date} at {instance.requested_time}.",
                    icon="calendar_month"
                )
        elif instance.status == 'Rejected':
            if employee:
                reason_str = f" Reason: {instance.rejection_reason}" if instance.rejection_reason else ""
                Notification.objects.create(
                    user=employee,
                    title="Reschedule Declined",
                    message=f"Your exit interview reschedule request was declined.{reason_str}",
                    icon="warning"
                )


@receiver(post_save, sender=ExitChecklistTask)
def notify_checklist_task_changes(sender, instance, created, **kwargs):
    if not created and instance.status == 'Completed':
        employee = AppUser.objects.filter(email=instance.resignation.email).first()
        if employee:
            Notification.objects.get_or_create(
                user=employee,
                title="Checklist Task Completed",
                message=f"Exit checklist task '{instance.title}' has been marked as Completed.",
                icon="check_circle"
            )
