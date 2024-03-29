#!/bin/bash
source activate usi

gunicorn -w 8 --threads=8 -b 0.0.0.0:5000 main:app --chdir metabolomics_spectrum_resolver --access-logfile /app/logs/access.log --timeout 90 --max-requests 100 --max-requests-jitter 20
