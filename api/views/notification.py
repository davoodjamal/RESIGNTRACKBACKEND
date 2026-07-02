from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import Notification, AppUser
from ..serializers import NotificationSerializer

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
