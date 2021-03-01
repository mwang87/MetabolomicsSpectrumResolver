#!/bin/bash
source activate usi

gunicorn -w 2 --threads=1 -b 0.0.0.0:5000 --timeout 3600 main:app --access-logfile /app/logs/access.log --timeout 30 --max-requests 500 --max-requests-jitter 100