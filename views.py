# views.py
from flask import abort, jsonify, render_template, request, redirect, url_for, send_file, make_response

from app import app

import os
import csv
import json
import uuid
import requests
import qrcode


from spectrum_utils import spectrum as spectrum_plotter_spectrum
from spectrum_utils import plot as spectrum_plotter_plot
import matplotlib.pyplot as plt


@app.route('/', methods=['GET'])
def renderhomepage():
    return render_template('index.html')

@app.route('/heartbeat', methods=['GET'])
def testapi():
    return_obj = {}
    return_obj["status"] = "fail"
    return json.dumps(return_obj)

@app.route('/test', methods=['GET'])
# to be deleted - just simon experimenting..
def example_spectrum_grab():
    request_url = 'https://massive.ucsd.edu/ProteoSAFe/DownloadResultFile?invoke=annotatedSpectrumImageText&block=0&file=FILE-%3EMSV000079514%2Fccms_peak%2FRAW%2FFrontal%20cortex%2FLTQ-Orbitrap%20Elite%2F85%2FAdult_Frontalcortex_bRP_Elite_85_f09.mzXML&scan=17555&peptide=*..*&uploadfile=True&task=4f2ac74ea114401787a7e96e143bb4a1'
    response = requests.get(request_url)
    spectrum = parsetext(response.text)
    return json.dumps(spectrum)

@app.route('/spectrum/',methods=['GET'])
def renderspectrum():
    task = request.args.get('task')
    filename = request.args.get('file')
    scan = request.args.get('scan')
    request_url = 'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?task={}&invoke=annotatedSpectrumImageText&block=0&file=FILE->{}&scan={}&peptide=*..*&force=false&_=1561457932129'.format(
        task,filename,scan
    )

    response = requests.get(request_url)
    spectrum = parsetext(response.text)

    identifier = "mzdata:GNPSTASK-%s:%s:scan:%s" % (task, filename, scan)

    masses, intentisities = zip(*spectrum['peaks'])

    spec = spectrum_plotter_spectrum.MsmsSpectrum(identifier, 0.0, 0.0,
                            masses, intentisities)

    spectrum_plotter_plot.spectrum(spec)
    plt.savefig("test.svg")
    spectrum_svg = open('test.svg').read()

    return render_template('spectrum.html', \
        peaks=json.dumps(spectrum['peaks']), \
        identifier=identifier, \
        task=task, \
        filename=filename, \
        scan=scan,
        spectrum_svg=spectrum_svg)

@app.route("/qrcode")
def generateQRImage():
    task = request.args.get('task')
    filename = request.args.get('file')
    scan = request.args.get('scan')

    identifier = "mzdata:GNPSTASK-%s:%s:scan:%s" % (task, filename, scan)

    #QR Code Rendering
    qr_image = qrcode.make(identifier)
    qr_image.save("image.png")

    return send_file("image.png")

@app.route('/lori',methods=['GET'])
def lorikeet_example():
    # render the lorikeet example - ensures that js and css is being imported
    return render_template('example_use.html',text = "boo")

def parsetext(text):
    lines = text.split('\n')
    # first 8 lines are header
    lines = lines[8:]
    peaks = []
    for line in lines:
        tokens = line.split()
        if len(tokens) == 0: # final line?
            continue 
        peaks.append((float(tokens[0]),float(tokens[1])))
    peaks.sort(key = lambda x: x[0]) # make sure sorted by m/z
    spectrum = {}
    spectrum['peaks'] = peaks
    spectrum['n_peaks'] = len(peaks)
    return spectrum
    
