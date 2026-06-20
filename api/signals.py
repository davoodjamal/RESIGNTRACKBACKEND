from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Resignation

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
