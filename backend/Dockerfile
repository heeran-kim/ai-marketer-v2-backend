FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install watchdog

# Ensure the script is executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "unset WERKZEUG_SERVER_FD && watchmedo auto-restart --patterns='*.py' --ignore-patterns='site-packages/**,*.log,*.sqlite3,*.pyc,__pycache__/**' --ignore-directories --recursive -- python manage.py runserver_plus --reloader-type stat --cert-file /app/localhost.pem --key-file /app/localhost-key.pem 0.0.0.0:8000"]