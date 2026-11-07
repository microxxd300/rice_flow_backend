#!/bin/sh
# Container start: apply migrations, collect static files, then hand off to gunicorn
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Model files are not in git or the image: train them on first start (a few seconds)
[ -f models/trained/yield_linear.pkl ] || python manage.py train_yield_models
[ -f models/trained/kmeans.pkl ] || python manage.py train_cluster_models

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout 120 \
    --access-logfile -
