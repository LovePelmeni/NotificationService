#!/bin/sh


echo "Starting Migrations."
python manage.py makemigrations
echo "Made."
python manage.py migrate


python manage.py createsuperuser --username ${SUPERUSER_USERNAME} \
--password ${SUPERUSER_PASSWORD} --email ${SUPERUSER_EMAIL}

pytest -q main.tests
gunicorn NotificationApp.wsgi:application --host 0.0.0.0 --port 8099 --workers 4 --timeout 120