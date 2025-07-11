import io
import sys
from typing import Any, Tuple

import celery
import umami

celery_instance = celery.Celery(
    "tasks_analytics",
    backend="redis://metabolomicsusi-redis",
    broker="redis://metabolomicsusi-redis",
)

umami.set_url_base("https://analytics-api.gnps2.org/")
umami.set_website_id('2e8b3719-51ec-4786-9b29-3e9198c31ea5')
umami.set_hostname('analytics-api.gnps2.org')

celery_instance.conf.task_routes = {
    "metabolomics_spectrum_resolver.tasks_analytics._task_analytics_event": {
        "queue": "worker-analytics"
    },
}

def task_analytics_event(event_type: str) -> str:
    """
    Task to log an analytics event using umami.
    
    Args:
        event_type (str): The type of event to log.
        
    Returns:
        str: Confirmation message indicating the event was sent.
    """
    
    _task_analytics_event.apply_async(
            args=([event_type])
        )

    return f"Event '{event_type}' logged."

@celery_instance.task(time_limit=10)
def _task_analytics_event(event_type) -> str:
    umami.new_event(event_name=event_type)
    
