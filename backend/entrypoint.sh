#!/bin/sh

set -e  # Exit immediately if a command fails

if [ "$1" = "celery" ]; then
  shift
  exec celery -A config.celery_app.app worker "$@"
  return
fi

ENV_FILE="/app/.env"
echo "🚀 Starting AI Marketer Backend Service"

# Check and create .env file if needed
if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

# Generate SECRET_KEY if needed
if ! grep -q "^SECRET_KEY=" "$ENV_FILE"; then
  SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
  echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
fi
echo "✓ SECRET_KEY setup done"

# Generate TWOFA_ENCRYPTION_KEY if needed
if ! grep -q "^TWOFA_ENCRYPTION_KEY=" "$ENV_FILE"; then
  TWOFA_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  echo "TWOFA_ENCRYPTION_KEY=$TWOFA_ENCRYPTION_KEY" >> "$ENV_FILE"
fi
echo "✓ TWOFA_ENCRYPTION_KEY setup done"

# Dev mode: check for migrations
if [ "$DJANGO_ENV" = "development" ]; then
    echo "⚠️ DEV MODE: checking for migration changes"
    python manage.py makemigrations --check
fi

python manage.py migrate --noinput
echo "✓ Database setup done"

# Dev mode: reset database
if [ "$DJANGO_ENV" = "development" ]; then
  if [ "$FLUSH_DB" = "True" ]; then
      echo "⚠️ DEV MODE: Resetting database"
      python manage.py flush --noinput
  fi
fi

echo "✅ Server starting"

exec "$@"
