import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import AppUser

def set_all():
    for user in AppUser.objects.all():
        user.set_password('password123')
        user.raw_password = 'password123'
        user.save()
    print("Passwords set to 'password123' successfully!")

if __name__ == '__main__':
    set_all()
