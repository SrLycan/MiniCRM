#!/bin/sh
set -e

python manage.py migrate --noinput

if [ -n "$DEMO_USERNAME" ] && [ -n "$DEMO_PASSWORD" ]; then
  python manage.py seed_demo
fi

exec "$@"
