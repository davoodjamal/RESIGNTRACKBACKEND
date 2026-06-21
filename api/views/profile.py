from rest_framework import generics, permissions
from ..serializers import AppUserSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /api/users/me/ - Retrieve currently logged-in user's profile.
    PUT/PATCH /api/users/me/ - Update currently logged-in user's profile.
    """
    serializer_class = AppUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
