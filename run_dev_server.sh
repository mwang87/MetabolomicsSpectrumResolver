#!/bin/bash
source activate usi

export FLASK_ENV=development
export PYTHONPATH=${PYTHONPATH}:.
cd metabolomics_spectrum_resolver && python3 main.py
