#!/bin/sh

set -e  # エラーが発生したら即時終了

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting Django application..."
exec "$@"
