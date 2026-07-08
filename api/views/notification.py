from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Notification, AppUser, Announcement
from ..serializers import NotificationSerializer, AnnouncementSerializer

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationMarkReadAllView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'All notifications marked as read'})

class NotificationMarkReadView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def post(self, request, pk, *args, **kwargs):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.is_read = True
            notif.save()
            return Response(NotificationSerializer(notif).data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


from rest_framework.views import APIView
from django.utils import timezone
import datetime

class BroadcastAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can broadcast announcements'}, status=status.HTTP_403_FORBIDDEN)
        
        title = request.data.get('title')
        message = request.data.get('message')
        expiry = request.data.get('expiry', 'never')
        
        if not title or not message:
            return Response({'error': 'Title and message are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        expiry_time = None
        if expiry == '1h':
            expiry_time = timezone.now() + datetime.timedelta(hours=1)
        elif expiry == '24h':
            expiry_time = timezone.now() + datetime.timedelta(days=1)
        elif expiry == '7d':
            expiry_time = timezone.now() + datetime.timedelta(days=7)
        
        # Clean up existing announcements first
        Announcement.objects.all().delete()
        Notification.objects.filter(icon='campaign').delete()
        
        # Create new Announcement
        announcement = Announcement.objects.create(
            title=title,
            message=message,
            expiry=expiry,
            expiry_time=expiry_time,
            created_by=request.user
        )
        
        # Create notifications for all users
        users = AppUser.objects.all()
        notifications = [
            Notification(user=u, title=f"Announcement: {title}", message=message, icon='campaign')
            for u in users
        ]
        Notification.objects.bulk_create(notifications)
        
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


class LatestAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ann = Announcement.objects.order_by('-created_at').first()
        if ann:
            if ann.expiry_time and ann.expiry_time < timezone.now():
                ann.delete()
                Notification.objects.filter(icon='campaign').delete()
                return Response(None, status=status.HTTP_200_OK)
            return Response(AnnouncementSerializer(ann).data, status=status.HTTP_200_OK)
        return Response(None, status=status.HTTP_200_OK)


class ActiveAnnouncementDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can delete announcements'}, status=status.HTTP_403_FORBIDDEN)
        
        Announcement.objects.all().delete()
        Notification.objects.filter(icon='campaign').delete()
        return Response({'status': 'Active announcement deleted successfully'}, status=status.HTTP_200_OK)


def create_notification(user, title, message, icon='notifications'):
    """
    Utility function to create a notification for a user.
    """
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        icon=icon
    )

