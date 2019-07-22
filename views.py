# views.py
from flask import abort, jsonify, render_template, request, redirect, url_for, send_file, make_response

from app import app

import os
import csv
import json
import uuid
import requests
import qrcode
import requests
import requests_cache
import parsing

from spectrum_utils import spectrum as spectrum_plotter_spectrum
from spectrum_utils import plot as spectrum_plotter_plot
import matplotlib.pyplot as plt

requests_cache.install_cache('demo_cache',expire_after=300)

SERVER = 'http://localhost:5000'
MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'

@app.route('/', methods=['GET'])
def renderhomepage():
    return render_template('homepage.html')

@app.route('/heartbeat', methods=['GET'])
def testapi():
    return_obj = {}
    return_obj["status"] = "fail"
    return json.dumps(return_obj)

@app.route('/spectrum/',methods=['GET'])
def renderspectrum():
    usi = request.args.get('usi')

    usi_identifier = usi.split(":")[1]

    if usi_identifier.startswith('GNPSTASK'):
        spectrum = parse_gnps_task(usi)
    elif usi_identifier.startswith('GNPSLIBRARY'):
        spectrum = parse_gnps_library(usi)
    elif usi_identifier.startswith('MS2LDATASK'):
        spectrum = parse_ms2lda(usi)
    elif usi_identifier.startswith('PXD000561'):
        spectrum = parse_MSV_PXD(usi)
    
    identifier = usi
    return render_template('spectrum.html', \
        peaks=json.dumps(spectrum['peaks']), \
        identifier=identifier, \
        )

#parsing MS2LDA in ms2lda.org
def parse_ms2lda(usi):
    tokens = usi.split(':')
    experiment_id = tokens[1].split('-')[1]
    filename = tokens[2]
    document_id = tokens[4]
    request_url = MS2LDA_SERVER + 'get_doc/?experiment_id={}&document_id={}'.format(
        experiment_id,
        document_id,
    )
    response = requests.get(request_url)
    peak_list = [(m,i) for m,i in json.loads(response.text)]
    peak_list.sort(key = lambda x: x[0])
    spectrum = {'peaks':peak_list}
    return spectrum

#parsing GNPS clustered spectra in Molecular Networking
def parse_gnps_task(usi):
    tokens = usi.split(':')

    task = tokens[1].split('-')[1]
    filename = tokens[2]
    scan = tokens[4]
    request_url = 'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?task={}&invoke=annotatedSpectrumImageText&block=0&file=FILE->{}&scan={}&peptide=*..*&force=false&_=1561457932129'.format(
        task,filename,scan
    )
    print(request_url)

    response = requests.get(request_url)
    spectrum = parsing.parse_gnps_peak_text(response.text)
    return spectrum

#parsing GNPS library
def parse_gnps_library(usi):
    tokens = usi.split(':')

    identifier= tokens[2]
    
    request_url = "https://gnps.ucsd.edu/ProteoSAFe/SpectrumCommentServlet?SpectrumID=%s" % (identifier)

    print(request_url)

    response = requests.get(request_url)

    peaks = json.loads(response.json()["spectruminfo"]["peaks_json"])    

    spectrum = {}
    spectrum['peaks'] = peaks
    spectrum['n_peaks'] = len(peaks)

    return spectrum

#parsing MSV or PXD library
def parse_MSV_PXD(usi):
    tokens = usi.split(':')

    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]

    lookup_url = "https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?id=mzspec:%s:%s:scan:%s" % (dataset_identifier, filename, scan)
    lookup_response = requests.get(lookup_url)

    lookup_dict = lookup_response.json()
    for found_scan in lookup_dict["row_data"]:
        if "mzML" in found_scan["file_descriptor"] or "mzXML" in found_scan["file_descriptor"] or "MGF" in found_scan["file_descriptor"] or "mgf" in found_scan["file_descriptor"]:
            request_url = 'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?task={}&invoke=annotatedSpectrumImageText&block=0&file=FILE->{}&scan={}&peptide=*..*&force=false&uploadfile=True'.format(
                "4f2ac74ea114401787a7e96e143bb4a1",found_scan["file_descriptor"],scan
            )

            spectrum_response = requests.get(request_url)

            spectrum = parsing.parse_gnps_peak_text(spectrum_response.text)
            return spectrum
    return None

@app.route("/svg/")
def generateSVG():

    try:
        xmin = float(request.args.get('xmin',None))
    except:
        xmin = None

    try:
        xmax = float(request.args.get('xmax',None))
    except:
        xmax = None

    usi = request.args.get('usi')

    usi_identifier = usi.split(":")[1]

    if usi_identifier.startswith('GNPSTASK'):
        spectrum = parse_gnps_task(usi)
    elif usi_identifier.startswith('GNPSLIBRARY'):
        spectrum = parse_gnps_library(usi)
    elif usi_identifier.startswith('MS2LDATASK'):
        spectrum = parse_ms2lda(usi)
    elif usi_identifier.startswith('PXD000561'):
        spectrum = parse_MSV_PXD(usi)


    if 'rescale' in request.args:
        if xmin:
            spectrum['peaks'] = list(filter(lambda x: x[0]>=xmin,spectrum['peaks']))
        if xmax:
            spectrum['peaks'] = list(filter(lambda x: x[0]<=xmax,spectrum['peaks']))
    masses, intentisities = zip(*spectrum['peaks'])

    

    fig = plt.figure(figsize=(10,6))

    spec = spectrum_plotter_spectrum.MsmsSpectrum(usi, 0.0, 0.0,
                            masses, intentisities)

    
    spectrum_plotter_plot.spectrum(spec)
    old_x_range = plt.xlim()
    new_x_range = list(old_x_range)
    if xmin:
        new_x_range[0] = xmin
    if xmax:
        new_x_range[1] = xmax
    
    plt.xlim(new_x_range)


    fig.suptitle(usi,fontsize=10)
    # ax = plt.gca()
    # h = plt.text(0.9,1.01,'usi link',url=SERVER+'/spectrum/?usi=' + usi ,transform=ax.transAxes)

    output_filename = os.path.join("/temp", str(uuid.uuid4()) + ".svg")

    plt.savefig(output_filename)

    spectrum_svg = open(output_filename).read()
    spectrum_svg = spectrum_svg.replace('white-space:pre;','')
    with open(output_filename,'w') as f:
        f.write(spectrum_svg)
    return send_file(output_filename,mimetype='image/svg+xml')



@app.route("/qrcode/")
def generateQRImage():
    # task = request.args.get('task')
    # filename = request.args.get('file')
    # scan = request.args.get('scan')

    # identifier = "mzdata:GNPSTASK-%s:%s:scan:%s" % (task, filename, scan)

    identifier = request.args.get('usi')

    #QR Code Rendering
    qr_image = qrcode.make(SERVER + '/spectrum/?usi=' + identifier)
    qr_image.save("image.png")

    return send_file("image.png")









### Testing Below ###





@app.route('/lori',methods=['GET'])
def lorikeet_example():
    # render the lorikeet example - ensures that js and css is being imported
    return render_template('example_use.html',text = "boo")


    


@app.route('/test', methods=['GET'])
# to be deleted - just simon experimenting..
def example_spectrum_grab():
    request_url = 'https://massive.ucsd.edu/ProteoSAFe/DownloadResultFile?invoke=annotatedSpectrumImageText&block=0&file=FILE-%3EMSV000079514%2Fccms_peak%2FRAW%2FFrontal%20cortex%2FLTQ-Orbitrap%20Elite%2F85%2FAdult_Frontalcortex_bRP_Elite_85_f09.mzXML&scan=17555&peptide=*..*&uploadfile=True&task=4f2ac74ea114401787a7e96e143bb4a1'
    response = requests.get(request_url)
    spectrum = parsetext(response.text)
    return json.dumps(spectrum)