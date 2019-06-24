# views.py
from flask import abort, jsonify, render_template, request, redirect, url_for, send_file, make_response

from app import app
from models import *

import os
import csv
import json
import uuid
import requests

@app.route('/', methods=['GET'])
def renderhomepage():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def validate():
    request_file = request.files['file']

    local_filename = os.path.join(app.config['UPLOAD_FOLDER'], str(uuid.uuid4()))
    request_file.save(local_filename)


    response_dict = {}
    response_dict["stats"] = []
    num_lines = sum(1 for line in open(local_filename))
    response_dict["stats"].append({"type":"total_rows", "value":num_lines})

    try:
        os.remove(local_filename)
    except:
        print("Cannot Remove File")

    return json.dumps(response_dict)


@app.route('/heartbeat', methods=['GET'])
def testapi():
    return_obj = {}
    return_obj["status"] = "success"
    return json.dumps(return_obj)
