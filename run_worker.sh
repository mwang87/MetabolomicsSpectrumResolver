#!/bin/bash
source activate usi

export C_FORCE_ROOT="true"
#TODO: Make sure we don't run this worker as root
cd metabolomics_spectrum_resolver && celery -A tasks worker -l info --autoscale=10,1 -Q worker --max-tasks-per-child 10 --loglevel INFO
