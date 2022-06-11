#!/bin/sh

echo "Starting Migrations."
python manage.py makemigrations
echo "Made."
python manage.py migrate

pytest -q ./main/tests.py
gunicorn NotificationApp.wsgi:application --host 0.0.0.0 --port 8099 --workers 4 --timeout 120