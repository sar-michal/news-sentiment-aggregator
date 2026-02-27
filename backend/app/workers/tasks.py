from app.workers.celery_app import celery

@celery.task(ignore_result=True)
def test_task(word: str):
    print(f"CELERY WORKER: Successfully processed word -> {word}")
    return True