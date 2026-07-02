import json
import queue
from django.db import models
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.dateparse import parse_date

from ..models import AuditLog
from ..serializers import AuditLogSerializer
from .common import IsHROrAdmin

class SSEPubSub:
    def __init__(self):
        self.listeners = []

    def add_listener(self):
        q = queue.Queue(maxsize=200)
        self.listeners.append(q)
        return q

    def remove_listener(self, q):
        if q in self.listeners:
            self.listeners.remove(q)

    def broadcast(self, data):
        payload = f"data: {json.dumps(data)}\n\n"
        for q in self.listeners[:]:
            try:
                q.put_nowait(payload)
            except queue.Full:
                self.remove_listener(q)
            except Exception:
                self.remove_listener(q)

audit_log_pubsub = SSEPubSub()

@receiver(post_save, sender=AuditLog)
def broadcast_new_audit_log(sender, instance, created, **kwargs):
    if created:
        serializer = AuditLogSerializer(instance)
        audit_log_pubsub.broadcast(serializer.data)


class AdminAuditLogListView(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        queryset = AuditLog.objects.all().order_by('-time')

        search_query = request.query_params.get('search')
        action_type = request.query_params.get('actionType')
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        admin_id = request.query_params.get('adminId')
        page_str = request.query_params.get('page', '1')
        limit_str = request.query_params.get('limit', '5')

        # Filters
        if search_query:
            q_filter = models.Q(target__icontains=search_query) | models.Q(message__icontains=search_query)
            if search_query.isdigit():
                q_filter |= models.Q(id=search_query)
            queryset = queryset.filter(q_filter)

        if action_type and action_type not in ['All', 'All Actions']:
            queryset = queryset.filter(action=action_type)

        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                queryset = queryset.filter(time__date__gte=parsed_start)

        if end_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                queryset = queryset.filter(time__date__lte=parsed_end)

        if admin_id and admin_id not in ['All', 'All Admins']:
            if admin_id.isdigit():
                queryset = queryset.filter(user_id=int(admin_id))
            elif admin_id.lower() == 'system':
                queryset = queryset.filter(user_id__isnull=True)
            else:
                from ..models import AppUser
                matching_user_ids = AppUser.objects.filter(
                    models.Q(username__icontains=admin_id) | models.Q(full_name__icontains=admin_id)
                ).values_list('id', flat=True)
                queryset = queryset.filter(user_id__in=matching_user_ids)

        # Pagination
        try:
            page = int(page_str)
        except ValueError:
            page = 1

        try:
            limit = int(limit_str)
        except ValueError:
            limit = 5

        total = queryset.count()
        total_pages = max(1, (total + limit - 1) // limit)

        start = (page - 1) * limit
        end = start + limit
        sliced_qs = queryset[start:end]

        serializer = AuditLogSerializer(sliced_qs, many=True)

        return Response({
            "success": True,
            "data": {
                "logs": serializer.data,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": total_pages
            }
        }, status=status.HTTP_200_OK)


def admin_audit_logs_stream(request):
    q = audit_log_pubsub.add_listener()
    
    def event_stream():
        try:
            yield ": ok\n\n"
            while True:
                try:
                    data = q.get(timeout=30.0)
                    yield data
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            audit_log_pubsub.remove_listener(q)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    return response
