from celery import Celery

# It's good practice to name the celery app after the project or app module
# The first argument to Celery is the name of the current module.
# This is needed so that names can be generated automatically when tasks are defined in the __main__ module.
# Or, if you have a discovery mechanism, the name of the main app package.
app = Celery('app', include=[
    'app.tasks.trial_tasks',
    'app.tasks.simple_tasks'
])

# Load configuration from the celeryconfig.py module within the 'app' package
# The namespace argument means all Celery configuration options must be uppercase and start with CELERY_.
app.config_from_object('app.celeryconfig')

# Optional: Autodiscover tasks from all registered Django apps or other specified locations.
# This is useful if your tasks are spread across different modules and you want Celery to find them.
# For this to work effectively with 'app.celeryconfig', ensure 'imports' is set in celeryconfig.py
# or that 'include' in the Celery() constructor points to all task modules.
# If 'include' is already comprehensive, autodiscover_tasks might be redundant here.
# app.autodiscover_tasks()

if __name__ == '__main__':
    app.start() 