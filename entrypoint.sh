#!/usr/bin/env bash
# entrypoint.sh — Container startup script
# Waits for the database, runs migrations, then starts Django.
set -e

echo "[entrypoint] Waiting for database..."
python manage.py shell -c "
import sys, time, os
import django
django.setup()
from django.db import connections
from django.db.utils import OperationalError

retries = 30
for i in range(retries):
    try:
        connections['default'].ensure_connection()
        print('[entrypoint] Database ready.')
        break
    except OperationalError:
        print(f'[entrypoint] DB not ready, retrying ({i+1}/{retries})...')
        time.sleep(2)
else:
    print('[entrypoint] ERROR: database never became available.')
    sys.exit(1)
"

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Starting Django server on 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
