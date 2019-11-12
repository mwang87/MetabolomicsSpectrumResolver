import csv
import json
import os
import uuid

import flask
import matplotlib.pyplot as plt
import numpy as np
import qrcode
import requests
import requests_cache
from spectrum_utils import spectrum as spectrum_plotter_spectrum
from spectrum_utils import plot as spectrum_plotter_plot

import parsing
from app import app


requests_cache.install_cache('demo_cache', expire_after=300)

USI_SERVER = 'https://metabolomics-usi.ucsd.edu/'
MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'
MOTIFDB_SERVER = 'http://ms2lda.org/motifdb/'
MASSBANK_SERVER = 'https://massbank.us/rest/spectra/'


@app.route('/', methods=['GET'])
def render_homepage():
    return flask.render_template('homepage.html')


@app.route('/contributors', methods=['GET'])
def contributors():
    return flask.render_template('contributors.html')


@app.route('/heartbeat', methods=['GET'])
def test_api():
    return json.dumps({'status': 'fail'})


@app.route('/spectrum/', methods=['GET'])
def render_spectrum():
    usi = flask.request.args.get('usi')
    spectrum = parse_usi(usi)

    return flask.render_template(
        'spectrum.html', peaks=json.dumps(spectrum['peaks']), identifier=usi)


@app.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    spectrum1 = parse_usi(usi1)
    spectrum2 = parse_usi(usi2)

    return flask.render_template(
        'mirror.html',
        peaks1=json.dumps(spectrum1['peaks']),
        peaks2=json.dumps(spectrum2['peaks']),
        identifier1=usi1, identifier2=usi2)


@app.errorhandler(500)
def internal_error(error):
    return flask.render_template('500.html')


# Parse MS2LDA from ms2lda.org.
def parse_ms2lda(usi):
    tokens = usi.split(':')
    experiment_id = tokens[1].split('-')[1]
    document_id = tokens[3]
    request_url = (f'{MS2LDA_SERVER}get_doc/?experiment_id={experiment_id}'
                   f'&document_id={document_id}')
    response = requests.get(request_url)
    spec_dict = json.loads(response.text)
    spec_dict['peaks'].sort(key=lambda x: x[0])
    return spec_dict


# Parse MOTIFDB from ms2lda.org.
def parse_motifdb(usi):
    # E.g. mzspec:MOTIFDB:motif:motif_id.
    tokens = usi.split(':')
    motif_id = tokens[3]
    request_url = f'{MOTIFDB_SERVER}get_motif/{motif_id}'
    response = requests.get(request_url)
    peak_list = [(m, i) for m, i in json.loads(response.text)]
    peak_list.sort(key=lambda x: x[0])
    spectrum = {'peaks': peak_list}
    return spectrum


# Parse MassBank entry.
def parse_massbank(usi):
    # E.g. mzspec:MASSBANK:motif:motif_id.
    tokens = usi.split(':')
    massbank_id = tokens[2]
    request_url = f'{MASSBANK_SERVER}{massbank_id}'
    response = requests.get(request_url)
    peaks_string = response.json()['spectrum']
    peak_list = [(float(peak.split(':')[0]), float(peak.split(':')[1]))
                 for peak in peaks_string.split(' ')]
    peak_list.sort(key=lambda x: x[0])
    spectrum = {'peaks': peak_list}
    return spectrum


# Parse GNPS clustered spectra in Molecular Networking.
def parse_gnps_task(usi):
    tokens = usi.split(':')
    task = tokens[1].split('-')[1]
    filename = tokens[2]
    scan = tokens[4]
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?'
                   f'task={task}&invoke=annotatedSpectrumImageText&block=0&'
                   f'file=FILE->{filename}&scan={scan}&peptide=*..*&'
                   f'force=false&_=1561457932129')
    response = requests.get(request_url)
    spectrum = parsing.parse_gnps_peak_text(response.text)
    return spectrum


# Parse GNPS library.
def parse_gnps_library(usi):
    tokens = usi.split(':')
    identifier = tokens[2]
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/SpectrumCommentServlet?'
                   f'SpectrumID={identifier}')
    response = requests.get(request_url)
    peaks = json.loads(response.json()['spectruminfo']['peaks_json'])
    spectrum = {'peaks': peaks, 'n_peaks': len(peaks),
                'precursor_mz': float(response.json()
                                      ['annotations'][0]['Precursor_MZ'])}
    return spectrum


# Parse MSV or PXD library.
def parse_msv_pxd(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    lookup_url = (f'https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?'
                  f'id=mzspec:{dataset_identifier}:{filename}:scan:{scan}')
    lookup_response = requests.get(lookup_url)
    lookup_dict = lookup_response.json()
    for found_scan in lookup_dict['row_data']:
        if ('mzML' in found_scan['file_descriptor'] or
                'mzXML' in found_scan['file_descriptor'] or
                'MGF' in found_scan['file_descriptor'] or
                'mgf' in found_scan['file_descriptor']):
            request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                           f'DownloadResultFile?'
                           f'task=4f2ac74ea114401787a7e96e143bb4a1&'
                           f'invoke=annotatedSpectrumImageText&block=0&'
                           f'file=FILE->{found_scan["file_descriptor"]}&'
                           f'scan={scan}&peptide=*..*&force=false&'
                           f'uploadfile=True')
            spectrum_response = requests.get(request_url)
            spectrum = parsing.parse_gnps_peak_text(spectrum_response.text)
            return spectrum
    return None


def parse_mtbls(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    all_datasets = (requests.get(
        'https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp').json()
        ['datasets'])
    massive_identifier = None
    for dataset in all_datasets:
        if dataset_identifier in dataset['title']:
            massive_identifier = dataset['dataset']
            break
    if massive_identifier is None:
        return None
    return parse_msv_pxd(f'mzspec{massive_identifier}:{filename}:scan:{scan}')


def parse_metabolomics_workbench(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    all_datasets = (requests.get(
        'https://massive.ucsd.edu/ProteoSAFe/datasets_json.jsp').json()
        ['datasets'])
    massive_identifier = None
    for dataset in all_datasets:
        if dataset_identifier in dataset['title']:
            massive_identifier = dataset['dataset']
            break
    if massive_identifier is None:
        return None
    return parse_msv_pxd(f'mzspec:{massive_identifier}:{filename}:scan:{scan}')


def _prepare_spectrum(usi, **kwargs):
    masses, intensities = zip(*parse_usi(usi)['peaks'])
    spec = spectrum_plotter_spectrum.MsmsSpectrum(
        usi, 0.0, 0, masses, intensities)
    spec.scale_intensity(max_intensity=1)

    if kwargs.get('rescale', False):
        spec.set_mz_range(kwargs.get('xmin'), kwargs.get('xmax'))

    if kwargs.get('label', False):
        annotate_mz = generate_labels(spec, kwargs.get('thresh', 0.05))
        label_dp = kwargs.get('label_dp', 4)
        for mz in annotate_mz:
            lab_text = f'{mz:.{label_dp}f}'
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


@app.route('/png/')
def generate_png():
    usi = flask.request.args.get('usi')
    plot_pars = get_plot_pars(flask.request)
    output_filename = generate_figure(usi, 'png', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/png')


@app.route('/png/mirror/')
def generate_mirror_png():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plot_pars = get_plot_pars(flask.request)
    output_filename = generate_mirror_figure(usi1, usi2, 'png', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/png')


def get_plot_pars(request):
    try:
        xmin = float(request.args.get('xmin', None))
    except:
        xmin = None

    try:
        xmax = float(request.args.get('xmax', None))
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
        label_dp = int(request.args.get('label_dp', None))
    except:
        label_dp = 4

    plot_pars = {'xmin': xmin,
                 'xmax': xmax,
                 'rescale': rescale,
                 'label': label,
                 'thresh': thresh,
                 'rotation': rotation,
                 'label_dp': label_dp}

    return plot_pars


@app.route('/svg/')
def generate_svg():
    usi = flask.request.args.get('usi')
    plot_pars = get_plot_pars(flask.request)
    output_filename = generate_figure(usi, 'svg', **plot_pars)
    fix_svg(output_filename)
    return flask.send_file(output_filename, mimetype='image/svg+xml')


@app.route('/svg/mirror/')
def generate_mirror_svg():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plot_pars = get_plot_pars(flask.request)
    output_filename = generate_mirror_figure(usi1, usi2, 'svg', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/png')


def fix_svg(output_filename):
    # Remove the whitespace issue.
    spectrum_svg = open(output_filename).read()
    spectrum_svg = spectrum_svg.replace('white-space:pre;', '')
    with open(output_filename,'w') as f:
        f.write(spectrum_svg)


@app.route('/json/')
def peak_json():
    usi = flask.request.args.get('usi')
    spectrum = parse_usi(usi)
    # Return for JSON includes, peaks, n_peaks, and precursor_mz.
    if 'precursor_mz' not in spectrum:
        spectrum['precursor_mz'] = 0

    return flask.jsonify(spectrum)


@app.route('/csv/')
def peak_csv():
    usi = flask.request.args.get('usi')
    spectrum = parse_usi(usi)
    output_filename = os.path.join(app.config['TEMPFOLDER'],
                                   str(uuid.uuid4()) + ".csv")
    with open(output_filename, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['mz', 'intensity'])
        for line in spectrum['peaks']:
            writer.writerow(line)
    return flask.send_file(output_filename, mimetype='text/csv',
                           as_attachment=True, attachment_filename='peaks.csv')


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

@app.route('/qrcode/')
def generateQRImage():
    identifier = flask.request.args.get('usi')
    # QR code rendering.
    qr_image = qrcode.make(f'{USI_SERVER}spectrum/?usi={identifier}')
    qr_image.save('image.png')
    return flask.send_file('image.png')


def parse_usi(usi):
    usi_identifier = usi.split(':')[1]
    if usi_identifier.startswith('GNPSTASK'):
        spectrum = parse_gnps_task(usi)
    elif usi_identifier.startswith('GNPSLIBRARY'):
        spectrum = parse_gnps_library(usi)
    elif usi_identifier.startswith('MS2LDATASK'):
        spectrum = parse_ms2lda(usi)
    elif usi_identifier.startswith('PXD'):
        spectrum = parse_msv_pxd(usi)
    elif usi_identifier.startswith('MSV'):
        spectrum = parse_msv_pxd(usi)
    elif usi_identifier.startswith('MTBLS'):
        spectrum = parse_mtbls(usi)
    elif usi_identifier.startswith('ST'):
        spectrum = parse_metabolomics_workbench(usi)
    elif usi_identifier.startswith('MOTIFDB'):
        spectrum = parse_motifdb(usi)
    elif usi_identifier.startswith('MASSBANK'):
        spectrum = parse_massbank(usi)
    return spectrum
