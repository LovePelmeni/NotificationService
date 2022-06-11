#!/bin/sh

echo "Starting Migrations."
python manage.py makemigrations
echo "Made."
if [$? -ne 0]; then
echo "Failed to run module tests. Exiting..."
exit 1;
fi

echo "Migrating..."
python manage.py migrate

if [$? -ne 0]; then
echo "Failed to migrate. Exiting..."
exit 1;
fi

gunicorn NotificationApp.wsgi:application --bind 0.0.0.0:8099 --workers 5 --timeout 120
if [$? -ne 0]; then
echo "Failed to run module tests. Exiting..."
exit 1;
fi