#!/bin/bash
source activate usi

export C_FORCE_ROOT="true"

# Running an analytics worker
celery -A metabolomics_spectrum_resolver.tasks_analytics worker --concurrency=1 -Q worker-analytics --loglevel INFO --detach

#TODO: Make sure we don't run this worker as root
celery -A metabolomics_spectrum_resolver.tasks worker -l info --autoscale=16,1 -Q worker --max-tasks-per-child 10 --loglevel INFO
