import os
from pathlib import Path
from dotenv import load_dotenv

# Determine the path to the .env.dev file relative to this config file
# This file is in app/, .env.dev is in the parent directory (api/)
ENV_PATH = Path(__file__).resolve().parent.parent / '.env.dev'
load_dotenv(dotenv_path=ENV_PATH)

# Default to Redis on localhost if not set in environment or .env.dev
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

broker_url = CELERY_BROKER_URL
result_backend = CELERY_RESULT_BACKEND
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Asia/Taipei'  # You might want to make this configurable via .env too
enable_utc = True
# The 'include' for tasks is usually kept in celery_app.py or handled by autodiscover_tasks
# If you want to specify it here, use 'imports'
# imports = ('app.tasks.trial_tasks',) 