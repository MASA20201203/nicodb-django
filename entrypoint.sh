#!/bin/sh

# set -e  # エラーが発生したら即時終了

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Changing ownership..."
chown -R www-data:www-data /app/staticfiles

echo "Starting Django application..."
exec "$@"
