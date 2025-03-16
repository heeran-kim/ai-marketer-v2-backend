#!/bin/sh

set -e  # Exit immediately if a command fails

echo "Checking for SECRET_KEY in .env..."
if ! grep -q "SECRET_KEY=" /app/.env; then
  echo "Generating SECRET_KEY..."
  echo "SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key(); print(get_random_secret_key())')" >> /app/.env
fi

echo "Making database migrations..."
python manage.py makemigrations --noinput

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Flushing database..."
python manage.py flush --noinput

echo "Loading fixture data..."
python manage.py loaddata users/fixtures/mock_users.json businesses/fixtures/mock_businesses.json social/fixtures/mock_social.json posts/fixtures/mock_posts.json promotions/fixtures/mock_promotions.json

exec "$@"
