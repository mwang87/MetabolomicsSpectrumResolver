from celery import Celery
from celery_once import QueueOnce
import sys
import parsing

celery_instance = Celery('tasks', 
  backend='redis://metabolomicsusi-redis', 
  broker='pyamqp://guest@metabolomicsusi-rabbitmq//'
  )

celery_instance.conf.update(
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle', 'json']
)

celery_instance.conf.ONCE = {
  'backend': 'celery_once.backends.Redis',
  'settings': {
    'url': 'redis://metabolomicsusi-redis:6379/0',
    'default_timeout': 60,
    'blocking' : True,
    'blocking_timeout' : 60
  }
}

@celery_instance.task(time_limit=60, base=QueueOnce)
def task_parse_usi(usi):
    spectrum, source, splash_key = parsing.parse_usi(usi)
    return spectrum, source, splash_key

@celery_instance.task(time_limit=60)
def task_computeheartbeat():
    print("UP", file=sys.stderr, flush=True)
    return "Up"


celery_instance.conf.task_routes = {
    'tasks.task_computeheartbeat': {'queue': 'worker'},
    'tasks.task_parse_usi': {'queue': 'worker'},
}