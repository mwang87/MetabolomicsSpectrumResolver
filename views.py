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
import numpy as np

from spectrum_utils import spectrum as spectrum_plotter_spectrum
from spectrum_utils import plot as spectrum_plotter_plot
import matplotlib.pyplot as plt

requests_cache.install_cache('demo_cache',expire_after=300)

SERVER = 'https://metabolomics-usi.ucsd.edu'
MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'
MOTIFDB_SERVER = 'http://ms2lda.org/motifdb/'
MASSBANK_SERVER = 'https://massbank.us/rest/spectra/'

@app.route('/', methods=['GET'])
def renderhomepage():
    return render_template('homepage.html')

@app.route('/contributors', methods=['GET'])
def contributors():
    return render_template('contributors.html')

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

@app.route('/mirror/',methods=['GET'])
def rendermirrorspectrum():
    usi1 = request.args.get('usi1')
    usi2 = request.args.get('usi2')
    spectrum1 = parse_USI(usi1)
    spectrum2 = parse_USI(usi2)

    return render_template('mirror.html', \
        peaks1=json.dumps(spectrum1['peaks']), \
        peaks2=json.dumps(spectrum2['peaks']), \
        identifier1=usi1, \
        identifier2=usi2, \
        )

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html')


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
    spec_dict = json.loads(response.text)
    spec_dict['peaks'].sort(key = lambda x: x[0])
    spectrum = spec_dict
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

#parsing massbank entry
def parse_massbank(usi):
    # e.g. mzspec:MASSBANK:motif:motif_id
    tokens = usi.split(':')
    massbank_id = tokens[2]
    request_url = MASSBANK_SERVER + '{}'.format(massbank_id)
    response = requests.get(request_url)
    peaks_string = response.json()["spectrum"]
    peak_list = [(float(peak.split(":")[0]), float(peak.split(":")[1])) for peak in peaks_string.split(" ")]
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

    response = requests.get(request_url)
    spectrum = parsing.parse_gnps_peak_text(response.text)
    return spectrum

#parsing GNPS library
def parse_gnps_library(usi):
    tokens = usi.split(':')

    identifier= tokens[2]

    request_url = "https://gnps.ucsd.edu/ProteoSAFe/SpectrumCommentServlet?SpectrumID=%s" % (identifier)

    response = requests.get(request_url)
    peaks = json.loads(response.json()["spectruminfo"]["peaks_json"])

    spectrum = {}
    spectrum['peaks'] = peaks
    spectrum['n_peaks'] = len(peaks)
    spectrum['precursor_mz'] = float(response.json()["annotations"][0]["Precursor_MZ"])

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


def _prepare_spectrum(usi, **kwargs):
    masses, intensities = zip(*parse_USI(usi)['peaks'])
    spec = spectrum_plotter_spectrum.MsmsSpectrum(
        usi, 0.0, 0, masses, intensities)
    spec.scale_intensity(max_intensity=1)

    if kwargs.get('rescale', False):
        spec.set_mz_range(kwargs.get('xmin'), kwargs.get('xmax'))

    if kwargs.get('label', False):
        annotate_mz = generate_labels(spec, kwargs.get('thresh', 0.05))
        label_dp = kwargs.get('label_dp',4)
        for mz in annotate_mz:
            lab_text = "{value:.{precision}f}".format(value=mz,precision=label_dp)
            spec.annotate_mz_fragment(mz, 0, 0.01, 'Da', text=lab_text)
            
    return spec


def generate_figure(usi, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 6))

    spec = _prepare_spectrum(usi, **kwargs)

    spectrum_plotter_plot.spectrum(
        spec, annot_kws={'rotation': kwargs.get('rotation', 70)}, ax=ax)

    xmin, xmax = ax.get_xlim()
    ax.set_xlim(kwargs.get('xmin', xmin), kwargs.get('xmax', xmax))
    if kwargs.get('label', False):
        ax.set_ylim(0, 1.5)

    fig.suptitle(usi, fontsize=10)

    output_filename = os.path.join(app.config['TEMPFOLDER'],
                                   f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)

    return output_filename


def generate_mirror_figure(usi1, usi2, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 6))

    spec1 = _prepare_spectrum(usi1, **kwargs)
    spec2 = _prepare_spectrum(usi2, **kwargs)

    spectrum_plotter_plot.mirror(spec1, spec2, ax=ax)

    xmin, xmax = ax.get_xlim()
    ax.set_xlim(kwargs.get('xmin', xmin), kwargs.get('xmax', xmax))
    if kwargs.get('label', False):
        ax.set_ylim(-1.5, 1.5)

    fig.suptitle(f'{usi1}={usi2}', fontsize=10)

    output_filename = os.path.join(app.config['TEMPFOLDER'],
                                   f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)

    return output_filename


@app.route("/png/")
def generatePNG():
    usi = request.args.get('usi')
    plot_pars = get_plot_pars(request)
    output_filename = generate_figure(usi, 'png', **plot_pars)
    return send_file(output_filename,mimetype='image/png')

@app.route("/png/mirror/")
def generateMirrorPNG():
    usi1 = request.args.get('usi1')
    usi2 = request.args.get('usi2')
    plot_pars = get_plot_pars(request)
    output_filename = generate_mirror_figure(usi1, usi2, 'png', **plot_pars)
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

    try:
        thresh = float(request.args.get('thresh', None))
    except:
        thresh = 0.1

    try:
        rotation = float(request.args.get('rotation', None))
    except:
        rotation = 70

    try:
        label_dp = int(request.args.get('label_dp',None))
    except:
        label_dp = 4

    plot_pars = {'xmin':xmin,
                 'xmax':xmax,
                 'rescale':rescale,
                 'label':label,
                 'thresh':thresh,
                 'rotation':rotation,
                 'label_dp':label_dp}
    
    return plot_pars

@app.route("/svg/")
def generateSVG():
    usi = request.args.get('usi')
    plot_pars = get_plot_pars(request)
    output_filename = generate_figure(usi, 'svg', **plot_pars)
    fix_svg(output_filename)
    return send_file(output_filename,mimetype='image/svg+xml')

@app.route("/svg/mirror/")
def generateMirrorSVG():
    usi1 = request.args.get('usi1')
    usi2 = request.args.get('usi2')
    plot_pars = get_plot_pars(request)
    output_filename = generate_mirror_figure(usi1, usi2, 'png', **plot_pars)
    return send_file(output_filename,mimetype='image/png')

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

    #Return for JSON includes, peaks, n_peaks, and precursor_mz

    if "precursor_mz" not in spectrum:
        spectrum["precursor_mz"] = 0

    return jsonify(spectrum)

@app.route("/csv/")
def peak_csv():
    usi = request.args.get('usi')
    spectrum = parse_USI(usi)
    output_filename = os.path.join(app.config['TEMPFOLDER'], str(uuid.uuid4()) + ".csv")
    with open(output_filename,'w') as f:
        writer = csv.writer(f)

        writer.writerow(['mz','intensity'])
        for line in spectrum['peaks']:
            writer.writerow(line)
    return send_file(output_filename,mimetype='text/csv',as_attachment=True,attachment_filename="peaks.csv")


def generate_labels(spec, intensity_threshold):
    mz_exclusion_window = (spec.mz[-1] - spec.mz[0]) / 20  # Max 20 labels.

    # Annotate peaks in decreasing intensity order.
    labeled_mz = []
    order = np.argsort(spec.intensity)[::-1]
    for mz, intensity in zip(spec.mz[order], spec.intensity[order]):
        if intensity < intensity_threshold:
            break
        else:
            if not any([abs(mz - already_labeled_mz) <= mz_exclusion_window
                        for already_labeled_mz in labeled_mz]):
                labeled_mz.append(mz)

    return labeled_mz

@app.route("/qrcode/")
def generateQRImage():
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
    elif usi_identifier.startswith('MASSBANK'):
        spectrum = parse_massbank(usi)

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
