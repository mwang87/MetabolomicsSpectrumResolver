from celery import Celery
import sys

celery_instance = Celery('tasks', backend='redis://metabolomicsusi-redis', broker='pyamqp://guest@metabolomicsusi-rabbitmq//', )

@celery_instance.task(time_limit=60)
def task_computeheartbeat():
    print("UP", file=sys.stderr, flush=True)
    return "Up"


celery_instance.conf.task_routes = {
    'tasks.task_computeheartbeat': {'queue': 'worker'},
}