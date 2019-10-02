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

SERVER = 'https://metabolomics-usi.ucsd.edu'
MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'
MOTIFDB_SERVER = 'http://ms2lda.org/motifdb/'

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
    spectrum = parse_USI(usi)

    return render_template('spectrum.html', \
        peaks=json.dumps(spectrum['peaks']), \
        identifier=usi, \
        )

#parsing MS2LDA in ms2lda.org
def parse_ms2lda(usi):
    tokens = usi.split(':')
    experiment_id = tokens[1].split('-')[1]
    filename = tokens[2]
    document_id = tokens[3]
    request_url = MS2LDA_SERVER + 'get_doc/?experiment_id={}&document_id={}'.format(
        experiment_id,
        document_id,
    )
    response = requests.get(request_url)
    peak_list = [(m,i) for m,i in json.loads(response.text)]
    peak_list.sort(key = lambda x: x[0])
    spectrum = {'peaks':peak_list}
    return spectrum

#parsing motifdb from ms2lda.org
def parse_motifdb(usi):
    # e.g. mzspec:MOTIFDB:motif:motif_id
    tokens = usi.split(':')
    motif_id = tokens[3]
    request_url = MOTIFDB_SERVER + 'get_motif/{}'.format(motif_id)
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

def parse_MTBLS(usi):
    tokens = usi.split(':')

    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]

    all_datasets = requests.get("https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp").json()["datasets"]
    massive_identifier = None

    for dataset in all_datasets:
        if dataset_identifier in dataset["title"]:
            massive_identifier = dataset["dataset"]
            break

    if massive_identifier == None:
        return None

    return parse_MSV_PXD("mzspec:%s:%s:scan:%s" % (massive_identifier, filename, scan))
    
def parse_MetabolomicsWorkbench(usi):
    tokens = usi.split(':')

    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]

    all_datasets = requests.get("https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp").json()["datasets"]
    massive_identifier = None

    for dataset in all_datasets:
        if dataset_identifier in dataset["title"]:
            massive_identifier = dataset["dataset"]
            break

    if massive_identifier == None:
        return None

    return parse_MSV_PXD("mzspec:%s:%s:scan:%s" % (massive_identifier, filename, scan))
    
def generate_figure(usi,format,xmin = None,xmax = None, rescale = False, label = False):
    spectrum = parse_USI(usi)

    if rescale:
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

    if label:
        labels = generate_labels(spectrum['peaks'],xmin,xmax)
        for label in labels:
            plt.text(label[0],label[1],label[2])
    
    output_filename = os.path.join(app.config['TEMPFOLDER'], str(uuid.uuid4()) + "." + format)
    plt.savefig(output_filename)

    return output_filename

    
   
@app.route("/png/")
def generatePNG():
    usi = request.args.get('usi')
    xmin,xmax,rescale,label = get_plot_pars(request)
    output_filename = generate_figure(usi,'png',xmin = xmin,xmax = xmax,rescale = rescale,label = label)
    return send_file(output_filename,mimetype='image/png')

def get_plot_pars(request):
    try:
        xmin = float(request.args.get('xmin',None))
    except:
        xmin = None

    try:
        xmax = float(request.args.get('xmax',None))
    except:
        xmax = None
    
    if 'rescale' in request.args:
        rescale = True
    else:
        rescale = False

    if 'label' in request.args:
        label = True
    else:
        label = False
    
    return xmin,xmax,rescale,label

@app.route("/svg/")
def generateSVG():
    usi = request.args.get('usi')
    xmin,xmax,rescale,label = get_plot_pars(request)
    output_filename = generate_figure(usi,'svg',xmin = xmin,xmax = xmax,rescale = rescale, label = label)
    fix_svg(output_filename)    
    return send_file(output_filename,mimetype='image/svg+xml')

def fix_svg(output_filename):
    # remove the whitespace issue
    spectrum_svg = open(output_filename).read()
    spectrum_svg = spectrum_svg.replace('white-space:pre;','')
    with open(output_filename,'w') as f:
        f.write(spectrum_svg)

@app.route("/json/")
def peak_json():
    usi = request.args.get('usi')
    spectrum = parse_USI(usi)
    return jsonify(spectrum)

@app.route("/csv/")
def peak_csv():
    usi = request.args.get('usi')
    spectrum = parse_USI(usi)
    output_filename = os.path.join(app.config['TEMPFOLDER'], str(uuid.uuid4()) + ".csv")
    with open(output_filename,'w') as f:
        writer = csv.writer(f)
        for line in spectrum['peaks']:
            writer.writerow(line)
    return send_file(output_filename,mimetype='text/csv',as_attachment=True,attachment_filename="peaks.csv")

# crude peak label generation!
def generate_labels(spectra,xmin,xmax):
    if xmin:
        spectra = list(filter(lambda x: x[0] >= xmin,spectra))
    if xmax:
        spectra = list(filter(lambda x: x[0] <= xmax,spectra))
    base_intensity = max([s[1] for s in spectra])
    spectra = list(filter(lambda x: x[1] >= base_intensity*0.5,spectra))
    print(spectra)
    labels = []
    for s in spectra:
        labels.append((s[0],0.01+s[1]/base_intensity,str(s[0])))
    return labels

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




def parse_USI(usi):
    usi_identifier = usi.split(":")[1]

    if usi_identifier.startswith('GNPSTASK'):
        spectrum = parse_gnps_task(usi)
    elif usi_identifier.startswith('GNPSLIBRARY'):
        spectrum = parse_gnps_library(usi)
    elif usi_identifier.startswith('MS2LDATASK'):
        spectrum = parse_ms2lda(usi)
    elif usi_identifier.startswith('PXD'):
        spectrum = parse_MSV_PXD(usi)
    elif usi_identifier.startswith('MSV'):
        spectrum = parse_MSV_PXD(usi)
    elif usi_identifier.startswith('MTBLS'):
        spectrum = parse_MTBLS(usi)
    elif usi_identifier.startswith('ST'):
        spectrum = parse_MetabolomicsWorkbench(usi)
    elif usi_identifier.startswith('MOTIFDB'):
        spectrum = parse_motifdb(usi)
        
    return spectrum




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