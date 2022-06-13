#!/bin/sh

PRODUCTION_DATABASE=${POSTGRES_DATABASE_PREFIX}
BACKUP_DATABASE=${BACKUP_DATABASE_PREFIX}


echo "Running migrations for backup database."
python manage.py makemigrations --database "$BACKUP_DATABASE"
echo "Made."
if [$? -ne 0]; then
echo "Failed to run module tests. Exiting..."
exit 1;
fi

echo "Migrating..."
python manage.py migrate

if [$? -ne 0]; then
echo "Failed to migrate to backup database. Exiting..."
exit 1;
fi


echo "Starting Migrations for production database."
python manage.py makemigrations --database "$PRODUCTION_DATABASE"
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

echo "Collecting Static content..."
python manage.py collectstatic --no-input

echo "Running Gunicorn server...."
gunicorn NotificationApp.wsgi:application --bind 0.0.0.0:8099 --workers 5 --timeout 120
if [$? -ne 0]; then
echo "Failed to run module tests. Exiting..."
exit 1;
fi