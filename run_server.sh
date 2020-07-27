#!/bin/bash
source activate usi

gunicorn -w 2 -b 0.0.0.0:5000 --timeout 3600 metabolomics_spectrum_resolver.app:app --access-logfile /app/logs/access.log --max-requests 1000
