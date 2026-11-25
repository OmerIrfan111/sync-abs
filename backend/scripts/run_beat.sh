#!/bin/sh
exec celery -A app.tasks.celery_app beat --loglevel=info
