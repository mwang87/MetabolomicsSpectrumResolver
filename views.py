import csv
import io
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

default_plotting_args = {'width': 10,
                         'height': 6,
                         'max_intensity': 1.25,
                         'grid': True,
                         'annotate_peaks': True,
                         'annotate_threshold': 0.05,
                         'annotate_precision': 4,
                         'annotation_rotation': 90}


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
    _, source_link = parsing.parse_usi(flask.request.args.get('usi'))
    return flask.render_template('spectrum.html',
                                 usi=flask.request.args.get('usi'),
                                 source_link=source_link)


@app.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    _, source1 = parsing.parse_usi(flask.request.args.get('usi1'))
    _, source2 = parsing.parse_usi(flask.request.args.get('usi2'))
    return flask.render_template('mirror.html',
                                 usi1=flask.request.args.get('usi1'),
                                 usi2=flask.request.args.get('usi2'),
                                 source_link1=source1, source_link2=source2)


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
    return flask.send_file(output_filename, mimetype='image/svg+xml')


@app.route('/svg/mirror/')
def generate_mirror_svg():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plot_pars = _get_plotting_args(flask.request)
    output_filename = _generate_mirror_figure(usi1, usi2, 'svg', **plot_pars)
    return flask.send_file(output_filename, mimetype='image/svg+xml')


def _generate_figure(usi, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    sup.spectrum(
        _prepare_spectrum(usi, **kwargs),
        annotate_ions=kwargs['annotate_peaks'],
        annot_kws={'rotation': kwargs['annotation_rotation']},
        grid=kwargs['grid'], ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(0, kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    ax.set_title(usi)

    plt.tight_layout()

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)
    plt.close()

    return output_filename


def _generate_mirror_figure(usi1, usi2, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    sup.mirror(_prepare_spectrum(usi1, **kwargs),
               _prepare_spectrum(usi2, **kwargs),
               {'annotate_ions': kwargs['annotate_peaks'],
                'annot_kws': {'rotation': kwargs['annotation_rotation']},
                'grid': kwargs['grid']}, ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(-kwargs['max_intensity'], kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    ax.set_title(f'Top: {usi1}\nBottom: {usi2}')

    plt.tight_layout()

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename)
    plt.close()

    return output_filename


def _prepare_spectrum(usi, **kwargs):
    spectrum, _ = parsing.parse_usi(usi)
    spectrum.scale_intensity(max_intensity=1)

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
    width = request.args.get('width')
    width = default_plotting_args['width'] if width is None else float(width)
    height = request.args.get('height')
    height = (default_plotting_args['height']
              if height is None else float(height))
    mz_min = request.args.get('mz_min')
    if mz_min is not None:
        mz_min = float(mz_min)
    mz_max = request.args.get('mz_max')
    if mz_max is not None:
        mz_max = float(mz_max)
    max_intensity = request.args.get('max_intensity')
    max_intensity = (default_plotting_args['max_intensity']
                     if max_intensity is None else float(max_intensity) / 100)
    grid = request.args.get('grid')
    grid = default_plotting_args['grid'] if grid is None else grid == 'true'
    annotate_peaks = request.args.get('annotate_peaks')
    annotate_peaks = (default_plotting_args['annotate_peaks']
                      if annotate_peaks is None else annotate_peaks == 'true')
    annotate_threshold = request.args.get('annotate_threshold')
    annotate_threshold = (default_plotting_args['annotate_threshold']
                          if annotate_threshold is None else
                          float(annotate_threshold) / 100)
    annotate_precision = request.args.get('annotate_precision')
    annotate_precision = (default_plotting_args['annotate_precision']
                          if annotate_precision is None
                          else int(annotate_precision))
    annotation_rotation = request.args.get('annotation_rotation')
    annotation_rotation = (default_plotting_args['annotation_rotation']
                           if annotation_rotation is None
                           else float(annotation_rotation))
    return {
        'width': width,
        'height': height,
        'mz_min': mz_min,
        'mz_max': mz_max,
        'max_intensity': max_intensity,
        'grid': grid,
        'annotate_peaks': annotate_peaks,
        'annotate_threshold': annotate_threshold,
        'annotate_precision': annotate_precision,
        'annotation_rotation': annotation_rotation}


@app.route('/json/')
def peak_json():
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    # Return for JSON includes, peaks, n_peaks, and precursor_mz.
    spectrum_dict = {'peaks': [(float(mz), float(intensity)) for mz, intensity
                               in zip(spectrum.mz, spectrum.intensity)],
                     'n_peaks': len(spectrum.mz),
                     'precursor_mz': spectrum.precursor_mz}
    return flask.jsonify(spectrum_dict)


@app.route('/csv/')
def peak_csv():
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    csv_str = io.StringIO()
    writer = csv.writer(csv_str)
    writer.writerow(['mz', 'intensity'])
    for mz, intensity in zip(spectrum.mz, spectrum.intensity):
        writer.writerow([mz, intensity])
    csv_bytes = io.BytesIO()
    csv_bytes.write(csv_str.getvalue().encode('utf-8'))
    csv_bytes.seek(0)
    return flask.send_file(csv_bytes, mimetype='text/csv', as_attachment=True,
                           attachment_filename=f'{spectrum.identifier}.csv')


@app.route('/qrcode/')
def generate_qr():
    # QR Code Rendering.
    if flask.request.args.get('mirror') != 'true':
        usi = flask.request.args.get('usi')
        url = f'{USI_SERVER}spectrum/?usi={usi}'
    else:
        usi1 = flask.request.args.get('usi1')
        usi2 = flask.request.args.get('usi2')
        url = f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}'
    qr_image = qrcode.make(url, box_size=2)
    qr_bytes = io.BytesIO()
    qr_image.save(qr_bytes, format='PNG')
    qr_bytes.seek(0)
    return flask.send_file(qr_bytes, 'image/png')


@app.errorhandler(500)
def internal_error(error):
    return flask.render_template('500.html')
