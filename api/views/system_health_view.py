import time
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .common import IsHROrAdmin

class SystemHealthV1View(APIView):
    permission_classes = [IsHROrAdmin]

    def get(self, request, *args, **kwargs):
        db_status = "Online"
        db_latency = "0ms"
        
        try:
            start_time = time.perf_counter()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            db_latency = f"{latency_ms}ms"
        except Exception:
            db_status = "Offline"
            db_latency = "0ms"
            
        # Server status is Healthy if database is online, otherwise Degraded.
        server_status = "Healthy" if db_status == "Online" else "Degraded"
        uptime_pct = "99.99%"
        
        return Response({
            "database": {
                "status": db_status,
                "latency": db_latency,
                "cluster": "Primary US-East Cluster"
            },
            "server": {
                "status": server_status,
                "uptime": uptime_pct
            }
        }, status=status.HTTP_200_OK)
