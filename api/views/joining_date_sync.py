import threading
import time
import requests
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache

from ..models import (
    CompanyMasterEmployee,
    HRManagementStaffProfile,
    UserDirectoryEmployeePersonal,
    JoiningDateAuditLog,
    SyncQueue,
    AppUser
)

# Thread-safe in-memory set to prevent concurrent modification loops
_locked_employees = set()
_lock = threading.Lock()

def acquire_lock(employee_id):
    with _lock:
        if employee_id in _locked_employees:
            return False
        _locked_employees.add(employee_id)
        return True

def release_lock(employee_id):
    with _lock:
        if employee_id in _locked_employees:
            _locked_employees.remove(employee_id)

def get_base_url(request=None):
    if request:
        return request.build_absolute_uri('/api').rstrip('/')
    return "http://127.0.0.1:8000/api"

class HRProfilePATCHView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        date_str = request.data.get('date')
        if not date_str:
            return Response({"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            profile, _ = HRManagementStaffProfile.objects.get_or_create(employee_id=id)
            profile.date_of_joining = date_str
            profile.save()
            return Response({"status": "Success", "message": "HR profile updated"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EmployeeDirectoryPATCHView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        date_str = request.data.get('date')
        if not date_str:
            return Response({"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            personal, _ = UserDirectoryEmployeePersonal.objects.get_or_create(employee_id=id)
            personal.hire_date = date_str
            personal.save()
            return Response({"status": "Success", "message": "Employee personal directory updated"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminJoiningDateOverrideView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id, *args, **kwargs):
        # Restriction: restricted to admin, SuperAdmin, or SystemAdmin roles
        user_role = request.user.role
        if user_role not in ['admin', 'SuperAdmin', 'SystemAdmin']:
            return Response({"error": "Unauthorized. Requires Admin credentials."}, status=status.HTTP_403_FORBIDDEN)

        date_str = request.data.get('date')
        if not date_str:
            return Response({"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Lock the field temporarily to prevent concurrent loops
        if not acquire_lock(id):
            return Response({"error": "Field is temporarily locked due to concurrent modification"}, status=status.HTTP_409_CONFLICT)

        try:
            # Retrieve previous value for audit logging
            admin_emp = CompanyMasterEmployee.objects.filter(employee_id=id).first()
            prev_date = admin_emp.joining_date if admin_emp else None

            # 2. Update Admin database
            if not admin_emp:
                admin_emp = CompanyMasterEmployee(employee_id=id)
            admin_emp.joining_date = date_str
            admin_emp.save()

            sync_status = {"admin": "Success", "hr": "Pending", "employee": "Pending"}
            headers = {"Authorization": request.headers.get('Authorization', '')}

            # 3. Force-push to HR Portal API endpoint
            hr_success = False
            base_url = get_base_url(request)
            try:
                res = requests.patch(
                    f"{base_url}/v1/hr/profile/{id}",
                    json={"date": date_str},
                    headers=headers,
                    timeout=3
                )
                if res.status_code == 200:
                    hr_success = True
                    sync_status["hr"] = "Success"
            except Exception:
                # Direct python fallback if server cannot reach itself
                try:
                    hr_prof, _ = HRManagementStaffProfile.objects.get_or_create(employee_id=id)
                    hr_prof.date_of_joining = date_str
                    hr_prof.save()
                    hr_success = True
                    sync_status["hr"] = "Success (Fallback)"
                except Exception:
                    pass

            if not hr_success:
                sync_status["hr"] = "Failed"
                SyncQueue.objects.create(employee_id=id, portal='hr', date_val=date_str, status='Pending')

            # Force-push to Employee Portal API endpoint
            emp_success = False
            try:
                res = requests.patch(
                    f"{base_url}/v1/employee/directory/{id}",
                    json={"date": date_str},
                    headers=headers,
                    timeout=3
                )
                if res.status_code == 200:
                    emp_success = True
                    sync_status["employee"] = "Success"
            except Exception:
                # Direct python fallback if server cannot reach itself
                try:
                    emp_pers, _ = UserDirectoryEmployeePersonal.objects.get_or_create(employee_id=id)
                    emp_pers.hire_date = date_str
                    emp_pers.save()
                    emp_success = True
                    sync_status["employee"] = "Success (Fallback)"
                except Exception:
                    pass

            if not emp_success:
                sync_status["employee"] = "Failed"
                SyncQueue.objects.create(employee_id=id, portal='employee', date_val=date_str, status='Pending')

            # 4. Perform post-sync handshake validation
            validation_ok = verify_sync_handshake(id, date_str)

            # Audit logging
            JoiningDateAuditLog.objects.create(
                employee_id=id,
                action_type="MANUAL_EDIT",
                previous_value=prev_date,
                new_value=date_str,
                actor=request.user.email or request.user.username,
                sync_status=sync_status
            )

            return Response({
                "status": "Success",
                "sync_status": sync_status,
                "validation_handshake": "Passed" if validation_ok else "Failed (Queued in DLQ)",
                "message": "Joining date updated and broadcast initiated."
            }, status=status.HTTP_200_OK)

        finally:
            # 5. Release field lock
            release_lock(id)

def verify_sync_handshake(employee_id, expected_date_str):
    try:
        admin_emp = CompanyMasterEmployee.objects.filter(employee_id=employee_id).first()
        hr_emp = HRManagementStaffProfile.objects.filter(employee_id=employee_id).first()
        emp_personal = UserDirectoryEmployeePersonal.objects.filter(employee_id=employee_id).first()

        admin_date = admin_emp.joining_date.strftime('%Y-%m-%d') if admin_emp and admin_emp.joining_date else None
        hr_date = hr_emp.date_of_joining.strftime('%Y-%m-%d') if hr_emp and hr_emp.date_of_joining else None
        emp_date = emp_personal.hire_date.strftime('%Y-%m-%d') if emp_personal and emp_personal.hire_date else None

        return admin_date == expected_date_str and hr_date == expected_date_str and emp_date == expected_date_str
    except Exception:
        return False


class JoiningDateAuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        logs = JoiningDateAuditLog.objects.all().order_by('-timestamp')[:50]
        data = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "employee_id": log.employee_id,
                "action_type": log.action_type,
                "previous_value": log.previous_value.strftime('%Y-%m-%d') if log.previous_value else None,
                "new_value": log.new_value.strftime('%Y-%m-%d') if log.new_value else None,
                "actor": log.actor,
                "sync_status": log.sync_status
            }
            for log in logs
        ]
        return Response(data, status=status.HTTP_200_OK)


# ─── DLQ background worker with Exponential Backoff ───
def run_dlq_worker():
    # Wait for the database connection and system initialization
    time.sleep(5)
    while True:
        try:
            pending_jobs = SyncQueue.objects.filter(status='Pending')
            for job in pending_jobs:
                # Exponential backoff delay: 2^retries seconds (max 5 retries)
                delay = 2 ** job.retries
                now = timezone.now()
                if (now - job.last_attempt).total_seconds() < delay:
                    continue

                success = False
                base_url = get_base_url()
                url = f"{base_url}/v1/hr/profile/{job.employee_id}" if job.portal == 'hr' else f"{base_url}/v1/employee/directory/{job.employee_id}"

                try:
                    res = requests.patch(url, json={"date": job.date_val.strftime('%Y-%m-%d')}, timeout=3)
                    if res.status_code == 200:
                        success = True
                except Exception:
                    # Python direct fallback
                    try:
                        if job.portal == 'hr':
                            prof, _ = HRManagementStaffProfile.objects.get_or_create(employee_id=job.employee_id)
                            prof.date_of_joining = job.date_val
                            prof.save()
                        else:
                            pers, _ = UserDirectoryEmployeePersonal.objects.get_or_create(employee_id=job.employee_id)
                            pers.hire_date = job.date_val
                            pers.save()
                        success = True
                    except Exception:
                        pass

                job.last_attempt = now
                if success:
                    job.status = 'Success'
                    job.save()

                    # Add audit log
                    JoiningDateAuditLog.objects.create(
                        employee_id=job.employee_id,
                        action_type=f"DLQ_RETRY_SUCCESS_{job.portal.upper()}",
                        previous_value=None,
                        new_value=job.date_val,
                        actor="DLQ Worker",
                        sync_status={job.portal: "Success"}
                    )
                else:
                    job.retries += 1
                    if job.retries >= 5:
                        job.status = 'Failed'
                    job.save()
        except Exception:
            pass
        time.sleep(5)

# Start DLQ thread daemonically
threading.Thread(target=run_dlq_worker, daemon=True).start()
