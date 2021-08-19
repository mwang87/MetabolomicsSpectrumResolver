#!/bin/bash
source activate usi

cd metabolomics_spectrum_resolver && gunicorn -w 4 --threads=8 -b 0.0.0.0:5000 main:app --access-logfile /app/logs/access.log --timeout 90 --max-requests 100 --max-requests-jitter 20
