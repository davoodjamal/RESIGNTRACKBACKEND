from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from ..models import ExitChecklistTask, Asset, AppUser, Resignation

class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'tasks': [], 'assets': [], 'users': [], 'resignations': []})

        user = request.user
        results = {}

        # 1. Search tasks
        if user.role in ['hr', 'admin']:
            tasks = ExitChecklistTask.objects.filter(
                models.Q(title__icontains=q) | models.Q(description__icontains=q)
            )
        else:
            tasks = ExitChecklistTask.objects.filter(
                resignation__email=user.email
            ).filter(
                models.Q(title__icontains=q) | models.Q(description__icontains=q)
            )
        results['tasks'] = [{
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'status': t.status,
            'type': 'task'
        } for t in tasks[:10]]

        # 2. Search assets
        if user.role in ['hr', 'admin']:
            assets = Asset.objects.filter(
                models.Q(name__icontains=q) | models.Q(tag__icontains=q) | models.Q(assigned_to__icontains=q)
            )
        else:
            assets = Asset.objects.filter(
                assigned_to=user.email
            ).filter(
                models.Q(name__icontains=q) | models.Q(tag__icontains=q)
            )
        results['assets'] = [{
            'id': a.id,
            'name': a.name,
            'tag': a.tag,
            'status': a.status,
            'type': 'asset'
        } for a in assets[:10]]

        # 3. Search users (Stakeholders/Employees)
        if user.role in ['hr', 'admin']:
            users = AppUser.objects.filter(
                models.Q(full_name__icontains=q) | models.Q(username__icontains=q) | models.Q(email__icontains=q) | models.Q(designation__icontains=q)
            )
        else:
            # Employees can search active stakeholders (HR and Admins)
            users = AppUser.objects.filter(
                role__in=['hr', 'admin']
            ).filter(
                models.Q(full_name__icontains=q) | models.Q(username__icontains=q) | models.Q(email__icontains=q) | models.Q(designation__icontains=q)
            )
        results['users'] = [{
            'id': u.id,
            'name': u.full_name or u.username,
            'email': u.email,
            'role': u.role,
            'designation': u.designation,
            'type': 'user'
        } for u in users[:10]]

        # 4. Search resignation cases
        if user.role in ['hr', 'admin']:
            resignations = Resignation.objects.filter(
                models.Q(name__icontains=q) | models.Q(email__icontains=q) | models.Q(reason__icontains=q)
            )
        else:
            resignations = Resignation.objects.filter(
                email=user.email
            ).filter(
                models.Q(reason__icontains=q) | models.Q(status__icontains=q)
            )
        results['resignations'] = [{
            'id': r.id,
            'name': r.name,
            'email': r.email,
            'status': r.status,
            'type': 'resignation'
        } for r in resignations[:10]]

        return Response(results)
