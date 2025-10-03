from celery import Celery
import os

# Get the broker URL from environment variables, with a default for local development
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create the Celery app instance
app = Celery(
    "tasks",
    broker=redis_url,
    backend=redis_url,
    include=["workers.tasks"],
)

# Optional: Configure other Celery settings
app.conf.update(
    task_track_started=True,
)

if __name__ == "__main__":
    app.start()
