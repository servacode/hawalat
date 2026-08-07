#!/usr/bin/env bash
# حوالات — إقلاع النسخة التجريبية على Render (خدمة واحدة تجمع كل شيء)
set -e
python manage.py migrate --no-input
python manage.py bootstrapadmin || true
celery -A config worker -l info --concurrency 1 &
celery -A config beat -l info &
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
