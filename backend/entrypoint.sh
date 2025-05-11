#!/bin/sh

set -e  # Exit immediately if a command fails

ENV_FILE="/app/.env"

if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

echo "Checking for SECRET_KEY in .env..."
if ! grep -q "^SECRET_KEY=" "$ENV_FILE"; then
  echo "Generating SECRET_KEY..."
  SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
  echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
fi

echo "Checking for TWOFA_ENCRYPTION_KEY in .env..."
if ! grep -q "^TWOFA_ENCRYPTION_KEY=" "$ENV_FILE"; then
  echo "Generating TWOFA_ENCRYPTION_KEY..."
  TWOFA_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo "TWOFA_ENCRYPTION_KEY=$TWOFA_ENCRYPTION_KEY" >> "$ENV_FILE"
fi

echo "Making database migrations..."
python manage.py makemigrations --noinput

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Flushing database..."
python manage.py flush --noinput # Comment if you dont want to flush the database

echo "Loading fixture data..."
python manage.py loaddata users/fixtures/mock_users.json businesses/fixtures/mock_businesses.json social/fixtures/mock_social.json

exec "$@"
