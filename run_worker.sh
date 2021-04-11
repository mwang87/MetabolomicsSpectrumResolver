#!/bin/bash
source activate usi

export C_FORCE_ROOT="true"
#TODO: Make sure we don't run this worker as root
celery -A tasks worker -l info -c 1 -Q worker --max-tasks-per-child 10 --loglevel INFO
