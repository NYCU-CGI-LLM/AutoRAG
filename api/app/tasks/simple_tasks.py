import time
from celery import shared_task
from app.celery_app import app # Corrected import for the Celery app instance

@shared_task(bind=True)
def reverse_string_task(self, text: str) -> str:
    """Simple Celery task that sleeps for 5 seconds and reverses a string."""
    print(f"Task {self.request.id}: Received text '{text}'")
    time.sleep(5)
    reversed_text = text[::-1]
    print(f"Task {self.request.id}: Reversed text to '{reversed_text}'")
    return reversed_text 