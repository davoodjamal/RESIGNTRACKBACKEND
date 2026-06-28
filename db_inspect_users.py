import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT id, email, username, role, raw_password FROM api_appuser")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
