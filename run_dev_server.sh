#!/bin/bash
source activate rdkit

export FLASK_ENV=development
python3 ./main.py
