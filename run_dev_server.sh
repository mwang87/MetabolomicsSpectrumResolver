#!/bin/bash
source activate usi

export FLASK_ENV=development
export PYTHONPATH=${PYTHONPATH}:.
python3 metabolomics_spectrum_resolver/main.py
