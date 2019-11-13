import csv
import json
import os
import uuid

import flask
import matplotlib.pyplot as plt
import numpy as np
import qrcode
import requests_cache
from spectrum_utils import plot as sup

import parsing
from app import app


requests_cache.install_cache('demo_cache', expire_after=300)

USI_SERVER = 'https://metabolomics-usi.ucsd.edu/'

default_plotting_args = {'annotate_threshold': 0.05,
                         'annotate_precision': 4,
                         'annotation_rotation': 70}


@app.route('/', methods=['GET'])
def render_homepage():
    return flask.render_template('homepage.html')


@app.route('/contributors', methods=['GET'])
def render_contributors():
    return flask.render_template('contributors.html')


@app.route('/heartbeat', methods=['GET'])
def render_heartbeat():
    return json.dumps({'status': 'fail'})


@app.route('/spectrum/', methods=['GET'])
def render_spectrum():
    # FIXME: It would be cleaner to remove the Lorikeet renderer or handle this
    #        differently.
    spectrum = parsing.parse_usi(flask.request.args.get('usi'))
    peaks = [(float(mz), float(intensity)) for mz, intensity
             in zip(spectrum.mz, spectrum.intensity)]
    return flask.render_template('spectrum.html',
                                 usi=flask.request.args.get('usi'),
                                 peaks=json.dumps(peaks))


@app.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    return flask.render_template('mirror.html',
                                 usi1=flask.request.args.get('usi1'),
                                 usi2=flask.request.args.get('usi2'))


@app.route('/png/')
def generate_png():
    usi = flask.request.args.get('usi')
    plotting_args = _get_plotting_args(flask.request)
    output_filename = _generate_figure(usi, 'png', **plotting_args)
    return flask.send_file(output_filename, mimetype='image/png')


@app.route('/png/mirror/')
def generate_mirror_png():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plot_pars = _get_plotting_args(flask.request)
    output_filename = _generate_mirror_figure(usi1, usi2, 'png', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/png')


@app.route('/svg/')
def generate_svg():
    usi = flask.request.args.get('usi')
    plot_pars = _get_plotting_args(flask.request)
    output_filename = _generate_figure(usi, 'svg', **plot_pars)
    _fix_svg_whitespace(output_filename)
    return flask.send_file(output_filename, mimetype='image/svg+xml')


@app.route('/svg/mirror/')
def generate_mirror_svg():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plot_pars = _get_plotting_args(flask.request)
    output_filename = _generate_mirror_figure(usi1, usi2, 'svg', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/svg+xml')


def _generate_figure(usi, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 6))

    sup.spectrum(
        _prepare_spectrum(usi, **kwargs),
        annot_kws={'rotation': kwargs['annotation_rotation']}, ax=ax)

    mz_min, mz_max = ax.get_xlim()
    ax.set_xlim(kwargs.get('mz_min', mz_min), kwargs.get('mz_max', mz_max))
    # Allow more space if the peaks are annotated.
    if kwargs['annotate_peaks']:
        ax.set_ylim(0, 1.5)

    fig.suptitle(usi, fontsize=10)

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)

    return output_filename


def _generate_mirror_figure(usi1, usi2, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 6))

    sup.mirror(_prepare_spectrum(usi1, **kwargs),
               _prepare_spectrum(usi2, **kwargs), ax=ax)

    mz_min, mz_max = ax.get_xlim()
    ax.set_xlim(kwargs.get('mz_min', mz_min), kwargs.get('mz_max', mz_max))
    # Allow more space if the peaks are annotated.
    if kwargs['annotate_peaks']:
        ax.set_ylim(-1.5, 1.5)

    fig.suptitle(f'{usi1}={usi2}', fontsize=10)

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)

    return output_filename


def _prepare_spectrum(usi, **kwargs):
    spectrum = parsing.parse_usi(usi)
    spectrum.scale_intensity(max_intensity=1)

    # TODO: This is not explicitly necessary.
    if kwargs['rescale_mz']:
        spectrum.set_mz_range(kwargs.get('mz_min'), kwargs.get('mz_max'))

    if kwargs['annotate_peaks']:
        for mz in _generate_labels(spectrum, kwargs['annotate_threshold']):
            spectrum.annotate_mz_fragment(
                mz, 0, 0.01, 'Da',
                text=f'{mz:.{kwargs["annotate_precision"]}f}')

    return spectrum


def _generate_labels(spec, intensity_threshold):
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


def _get_plotting_args(request):
    mz_min = request.args.get('mz_min')
    if mz_min is not None:
        mz_min = float(mz_min)
    mz_max = request.args.get('mz_max')
    if mz_max is not None:
        mz_max = float(mz_max)
    rescale_mz = 'rescale' in request.args
    annotate_peaks = 'annotate_peaks' in request.args
    annotate_threshold = float(request.args.get(
        'annotate_threshold', default_plotting_args['annotate_threshold']))
    annotate_precision = int(request.args.get(
        'annotate_precision', default_plotting_args['annotate_precision']))
    annotation_rotation = int(request.args.get(
        'annotation_rotation', default_plotting_args['annotation_rotation']))

    return {'mz_min': mz_min,
            'mz_max': mz_max,
            'rescale_mz': rescale_mz,
            'annotate_peaks': annotate_peaks,
            'annotate_threshold': annotate_threshold,
            'annotate_precision': annotate_precision,
            'annotation_rotation': annotation_rotation}


def _fix_svg_whitespace(output_filename):
    # Remove the whitespace issue.
    with open(output_filename, 'r+') as f:
        text = f.read().replace('white-space:pre;', '')
        f.seek(0)
        f.write(text)


@app.route('/json/')
def peak_json():
    spectrum = parsing.parse_usi(flask.request.args.get('usi'))
    # Return for JSON includes, peaks, n_peaks, and precursor_mz.
    spectrum_dict = {'peaks': [(float(mz), float(intensity)) for mz, intensity
                               in zip(spectrum.mz, spectrum.intensity)],
                     'n_peaks': len(spectrum.mz),
                     'precursor_mz': spectrum.precursor_mz}
    return flask.jsonify(spectrum_dict)


@app.route('/csv/')
def peak_csv():
    spectrum = parsing.parse_usi(flask.request.args.get('usi'))
    filename = os.path.join(app.config['TEMPFOLDER'], f'{uuid.uuid4()}.csv')
    with open(filename, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['mz', 'intensity'])
        for mz, intensity in zip(spectrum.mz, spectrum.intensity):
            writer.writerow([mz, intensity])
    return flask.send_file(filename, mimetype='text/csv',
                           as_attachment=True, attachment_filename='peaks.csv')


@app.route('/qrcode/')
def generate_qr_image():
    usi = flask.request.args.get('usi')
    # QR code rendering.
    qr_image = qrcode.make(f'{USI_SERVER}spectrum/?usi={usi}')
    qr_image.save('image.png')
    return flask.send_file('image.png')


@app.errorhandler(500)
def internal_error(error):
    return flask.render_template('500.html')
