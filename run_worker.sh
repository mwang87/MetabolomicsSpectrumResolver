#!/bin/bash
source activate usi

export C_FORCE_ROOT="true"
#TODO: Make sure we don't run this worker as root
celery -A metabolomics_spectrum_resolver.tasks worker -l info --autoscale=12,1 -Q worker --max-tasks-per-child 10 --loglevel INFO
