import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'api_appuser'")
    cols = cursor.fetchall()
    for col in cols:
        print(col)
