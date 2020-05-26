#!/bin/bash
source activate usi

gunicorn -w 2 -b 0.0.0.0:5000 --timeout 3600 main:app --access-logfile /app/logs/access.log --max-requests 1000
