#!/bin/bash
set -e

echo "Waiting for SQL Server and ZlapLokalDB..."
until python - <<'PY'
import os
import pyodbc
password = os.environ.get('MSSQL_SA_PASSWORD')
connection_string = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=db,1433;DATABASE=ZlapLokalDB;UID=sa;PWD=' + password + ';'
    'Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=5;'
)
with pyodbc.connect(connection_string) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Users'")
    row = cursor.fetchone()
    if not row:
        raise RuntimeError('Users table not ready yet')
PY
do
    sleep 3
done

python manage.py migrate

python manage.py shell <<'PY'
from django.contrib.auth.models import User
from api.models import Users

demo_users = [
    ('admin', 'admin@zlaplokal.pl', 'admin123', Users.ROLE_ADMIN),
    ('event_master', 'kontakt@event-space.pl', 'owner123', Users.ROLE_OWNER),
    ('janusz_biznesu', 'janusz.wlasciciel@gmail.com', 'owner123', Users.ROLE_OWNER),
    ('tomek_impreza', 'tomasz.imprezowicz@wp.pl', 'user123', Users.ROLE_RENTER),
    ('kasia_studentka', 'kasia.studentka@stud.pwr.edu.pl', 'user123', Users.ROLE_RENTER),
]

for username, email, password, role in demo_users:
    auth_user, _ = User.objects.update_or_create(
        username=username,
        defaults={
            'email': email,
            'is_active': True,
            'is_staff': role == Users.ROLE_ADMIN,
            'is_superuser': role == Users.ROLE_ADMIN,
        },
    )
    auth_user.set_password(password)
    auth_user.save()
    Users.objects.update_or_create(
        username=username,
        defaults={
            'email': email,
            'password_hash': 'HASHED_IN_DJANGO_AUTH_USER',
            'role': role,
            'is_active': True,
        },
    )

print('Demo users are ready.')
PY

python manage.py runserver 0.0.0.0:8000
