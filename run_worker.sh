#!/bin/bash
source activate usi

celery -A tasks worker -l info -c 1 -Q worker --max-tasks-per-child 10 --loglevel INFO
