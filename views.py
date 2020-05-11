import copy
import csv
import io
import json
import os
import uuid

import flask
import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import qrcode
import requests_cache
from spectrum_utils import plot as sup
from spectrum_utils import spectrum as sus

import parsing
from app import app


requests_cache.install_cache('demo_cache', expire_after=300)

USI_SERVER = 'https://metabolomics-usi.ucsd.edu/'

default_plotting_args = {'width': 10,
                         'height': 6,
                         'max_intensity_unlabeled': 1.05,
                         'max_intensity_labeled': 1.25,
                         'grid': True,
                         # List of peaks to annotate in the top/bottom
                         # spectrum.
                         'annotate_peaks': [[], []],
                         'annotate_threshold': 0.1,
                         'annotate_precision': 4,
                         'annotation_rotation': 90}


@app.route('/', methods=['GET'])
def render_homepage():
    return flask.render_template('homepage.html')


@app.route('/contributors', methods=['GET'])
def render_contributors():
    return flask.render_template('contributors.html')

@app.route('/dataprivacy', methods=['GET'])
def render_dataprivacy():
    return flask.render_template('dataprivacy.html')

@app.route('/heartbeat', methods=['GET'])
def render_heartbeat():
    return json.dumps({'status': 'success'})


@app.route('/spectrum/', methods=['GET'])
def render_spectrum():
    spectrum, source_link = parsing.parse_usi(flask.request.args.get('usi'))
    spectrum = copy.deepcopy(spectrum)
    spectrum.scale_intensity(max_intensity=1)
    annotations = np.zeros_like(spectrum.mz, np.bool)
    annotations[_generate_labels(
        spectrum, default_plotting_args['annotate_threshold'])] = True
    return flask.render_template(
        'spectrum.html', usi=flask.request.args.get('usi'),
        source_link=source_link,
        peaks=[[(float(mz), float(intensity), annotate)
                for mz, intensity, annotate in zip(
                spectrum.mz, spectrum.intensity, annotations)]])


@app.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    spectrum1, source1 = parsing.parse_usi(flask.request.args.get('usi1'))
    spectrum1 = copy.deepcopy(spectrum1)
    spectrum1.scale_intensity(max_intensity=1)
    annotations1 = np.zeros_like(spectrum1.mz, np.bool)
    annotations1[_generate_labels(
        spectrum1, default_plotting_args['annotate_threshold'])] = True
    spectrum2, source2 = parsing.parse_usi(flask.request.args.get('usi2'))
    spectrum2 = copy.deepcopy(spectrum2)
    spectrum2.scale_intensity(max_intensity=1)
    annotations2 = np.zeros_like(spectrum2.mz, np.bool)
    annotations2[_generate_labels(
        spectrum2, default_plotting_args['annotate_threshold'])] = True
    return flask.render_template(
        'mirror.html',
        usi1=flask.request.args.get('usi1'),
        usi2=flask.request.args.get('usi2'),
        source_link1=source1, source_link2=source2,
        peaks=[[(float(mz), float(intensity), annotate)
                for mz, intensity, annotate in zip(
                spectrum1.mz, spectrum1.intensity, annotations1)],
               [(float(mz), float(intensity), annotate)
                for mz, intensity, annotate in zip(
                   spectrum2.mz, spectrum2.intensity, annotations2)]])


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

    kwargs['annotate_peaks'] = kwargs['annotate_peaks'][0]
    spectrum = _prepare_spectrum(usi, **kwargs)
    sup.spectrum(
        spectrum, annotate_ions=kwargs['annotate_peaks'],
        annot_kws={'rotation': kwargs['annotation_rotation']},
        grid=kwargs['grid'], ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(0, kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    title = ax.text(0.5, 1.06, usi, horizontalalignment='center',
                    verticalalignment='bottom', fontsize='x-large',
                    fontweight='bold', transform=ax.transAxes)
    title.set_url(f'{USI_SERVER}spectrum/?usi={usi}')
    subtitle = (f'Precursor m/z: '
                f'{spectrum.precursor_mz:.{kwargs["annotate_precision"]}f} '
                if spectrum.precursor_mz > 0 else '')
    subtitle += f'Charge: {spectrum.precursor_charge}'
    subtitle = ax.text(0.5, 1.02, subtitle, horizontalalignment='center',
                       verticalalignment='bottom', fontsize='large',
                       transform=ax.transAxes)
    subtitle.set_url(f'{USI_SERVER}spectrum/?usi={usi}')

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename, bbox_inches='tight')
    plt.close()

    return output_filename


def _generate_mirror_figure(usi1, usi2, extension, **kwargs):
    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    annotate_peaks = kwargs['annotate_peaks']
    kwargs['annotate_peaks'] = annotate_peaks[0]
    spectrum_top = _prepare_spectrum(usi1, **kwargs)
    kwargs['annotate_peaks'] = annotate_peaks[1]
    spectrum_bottom = _prepare_spectrum(usi2, **kwargs)

    fragment_mz_tolerance = 0.02    # TODO: Configurable?

    if spectrum_top.annotation is None:
        spectrum_top.annotation = np.full_like(
            spectrum_top.mz, None, object)
    if spectrum_bottom.annotation is None:
        spectrum_bottom.annotation = np.full_like(
            spectrum_bottom.mz, None, object)
    for i, (annotation, mz) in enumerate(zip(spectrum_top.annotation,
                                             spectrum_top.mz)):
        if annotation is None:
            spectrum_top.annotation[i] = sus.FragmentAnnotation(0, mz, '')
        if np.min(np.abs(spectrum_bottom.mz - mz)) < fragment_mz_tolerance:
            spectrum_top.annotation[i].ion_type = 'top'
        else:
            spectrum_top.annotation[i].ion_type = 'unmatched'
    for i, (annotation, mz) in enumerate(zip(spectrum_bottom.annotation,
                                             spectrum_bottom.mz)):
        if annotation is None:
            spectrum_bottom.annotation[i] = sus.FragmentAnnotation(0, mz, '')
        if np.min(np.abs(spectrum_top.mz - mz)) < fragment_mz_tolerance:
            spectrum_bottom.annotation[i].ion_type = 'bottom'
        else:
            spectrum_bottom.annotation[i].ion_type = 'unmatched'

    # Colors for mirror plot peaks, subject to change.
    sup.colors['top'] = '#212121'
    sup.colors['bottom'] = '#388E3C'
    sup.colors['unmatched'] = 'darkgray'

    sup.mirror(spectrum_top, spectrum_bottom,
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

    title = ax.text(0.5, 1.19, f'Top: {usi1}', horizontalalignment='center',
                    verticalalignment='bottom', fontsize='x-large',
                    fontweight='bold', transform=ax.transAxes)
    title.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
    subtitle = (
        f'Precursor m/z: '
        f'{spectrum_top.precursor_mz:.{kwargs["annotate_precision"]}f} '
        if spectrum_top.precursor_mz > 0 else '')
    subtitle += f'Charge: {spectrum_top.precursor_charge}'
    subtitle = ax.text(0.5, 1.15, subtitle, horizontalalignment='center',
                       verticalalignment='bottom', fontsize='large',
                       transform=ax.transAxes)
    subtitle.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
    title = ax.text(0.5, 1.1, f'Bottom: {usi2}', horizontalalignment='center',
                    verticalalignment='bottom', fontsize='x-large',
                    fontweight='bold', transform=ax.transAxes)
    title.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
    subtitle = (
        f'Precursor m/z: '
        f'{spectrum_bottom.precursor_mz:.{kwargs["annotate_precision"]}f} '
        if spectrum_bottom.precursor_mz > 0 else '')
    subtitle += f'Charge: {spectrum_bottom.precursor_charge}'
    subtitle = ax.text(0.5, 1.06, subtitle, horizontalalignment='center',
                       verticalalignment='bottom', fontsize='large',
                       transform=ax.transAxes)
    subtitle.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')

    similarity = cosine(spectrum_top, spectrum_bottom, fragment_mz_tolerance)
    subtitle_score = f'Cosine similarity = {similarity:.4f}'
    ax.text(0.5, 1.02, subtitle_score, horizontalalignment='center',
            verticalalignment='bottom', fontsize='large',
            fontweight='bold', transform=ax.transAxes)

    output_filename = os.path.join(
        app.config['TEMPFOLDER'], f'{uuid.uuid4()}.{extension}')
    plt.savefig(output_filename, bbox_inches='tight')
    plt.close()

    return output_filename


def cosine(spectrum1: sus.MsmsSpectrum, spectrum2: sus.MsmsSpectrum,
           fragment_mz_tolerance: float) -> float:
    """
    Compute the cosine similarity between the given spectra.

    Parameters
    ----------
    spectrum1 : sus.MsmsSpectrum
        The first spectrum.
    spectrum2 : sus.MsmsSpectrum
        The second spectrum.
    fragment_mz_tolerance : float
        The fragment m/z tolerance used to match peaks.

    Returns
    -------
    float
        The cosine similarity between the given spectra.
    """
    return _cosine(spectrum1.mz, np.copy(spectrum1.intensity),
                   spectrum2.mz, np.copy(spectrum2.intensity),
                   fragment_mz_tolerance)


@nb.njit
def _cosine(mz: np.ndarray, intensity: np.ndarray, mz_other: np.ndarray,
            intensity_other: np.ndarray, fragment_mz_tol: float) -> float:
    """
    Compute the cosine similarity between the given spectra.

    Parameters
    ----------
    mz : np.ndarray
        The first spectrum's m/z values.
    intensity : np.ndarray
        The first spectrum's intensity values.
    mz_other : np.ndarray
        The second spectrum's m/z values.
    intensity_other : np.ndarray
        The second spectrum's intensity values.
    fragment_mz_tol : float
        The fragment m/z tolerance used to match peaks in both spectra with
        each other.

    Returns
    -------
    float
        The cosine similarity between both spectra.
    """
    intensity /= np.linalg.norm(intensity)
    intensity_other /= np.linalg.norm(intensity_other)
    # Find the matching peaks between both spectra.
    peak_match_scores, peak_match_idx = [], []
    peak_other_i = 0
    for peak_i, (peak_mz, peak_intensity) in enumerate(zip(mz, intensity)):
        # Advance while there is an excessive mass difference.
        while (peak_other_i < len(mz_other) - 1 and
               peak_mz - fragment_mz_tol > mz_other[peak_other_i]):
            peak_other_i += 1
        # Match the peaks within the fragment mass window if possible.
        peak_other_window_i = peak_other_i
        while (peak_other_window_i < len(mz_other) and
               abs(peak_mz - (mz_other[peak_other_window_i]))
               <= fragment_mz_tol):
            peak_match_scores.append(
                peak_intensity * intensity_other[peak_other_window_i])
            peak_match_idx.append((peak_i, peak_other_window_i))
            peak_other_window_i += 1

    score = 0
    if len(peak_match_scores) > 0:
        # Use the most prominent peak matches to compute the score (sort in
        # descending order).
        peak_match_scores_arr = np.asarray(peak_match_scores)
        peak_match_order = np.argsort(peak_match_scores_arr)[::-1]
        peak_match_scores_arr = peak_match_scores_arr[peak_match_order]
        peak_match_idx_arr = np.asarray(peak_match_idx)[peak_match_order]
        peaks_used, peaks_used_other = set(), set()
        for peak_match_score, peak_i, peak_other_i in zip(
                peak_match_scores_arr, peak_match_idx_arr[:, 0],
                peak_match_idx_arr[:, 1]):
            if (peak_i not in peaks_used and
                    peak_other_i not in peaks_used_other):
                score += peak_match_score
                # Make sure these peaks are not used anymore.
                peaks_used.add(peak_i)
                peaks_used_other.add(peak_other_i)

    return score


def _prepare_spectrum(usi, **kwargs):
    spectrum, _ = parsing.parse_usi(usi)
    spectrum = copy.deepcopy(spectrum)
    spectrum.scale_intensity(max_intensity=1)

    if kwargs['annotate_peaks']:
        if kwargs['annotate_peaks'] is True:
            kwargs['annotate_peaks'] = _generate_labels(
                spectrum, default_plotting_args['annotate_threshold'])
        for mz in kwargs['annotate_peaks']:
            t = f'{mz:.{kwargs["annotate_precision"]}f}'
            spectrum.annotate_mz_fragment(mz, 0, 0.01, 'Da', text=t)

    spectrum.set_mz_range(kwargs['mz_min'], kwargs['mz_max'])
    spectrum.scale_intensity(max_intensity=1)

    return spectrum


def _generate_labels(spec, intensity_threshold):
    mz_exclusion_window = (spec.mz[-1] - spec.mz[0]) / 20  # Max 20 labels.

    # Annotate peaks in decreasing intensity order.
    labeled_i, order = [], np.argsort(spec.intensity)[::-1]
    for i, mz, intensity in zip(order, spec.mz[order], spec.intensity[order]):
        if intensity < intensity_threshold:
            break
        else:
            if not any([abs(mz - spec.mz[already_labeled_i])
                        <= mz_exclusion_window
                        for already_labeled_i in labeled_i]):
                labeled_i.append(i)

    return labeled_i


def _get_plotting_args(request):
    plotting_args = {}
    width = request.args.get('width')
    plotting_args['width'] = (default_plotting_args['width']
                              if width is None else float(width))
    height = request.args.get('height')
    plotting_args['height'] = (default_plotting_args['height']
                               if height is None else float(height))
    mz_min = request.args.get('mz_min')
    plotting_args['mz_min'] = float(mz_min) if mz_min else None
    mz_max = request.args.get('mz_max')
    plotting_args['mz_max'] = float(mz_max) if mz_max else None
    grid = request.args.get('grid')
    plotting_args['grid'] = (default_plotting_args['grid']
                             if grid is None else grid == 'true')
    annotate_peaks_args = request.args.get('annotate_peaks')
    annotate_peaks = ([[mz for mz in peaks]
                       for peaks in json.loads(annotate_peaks_args)]
                      if annotate_peaks_args is not None else
                      default_plotting_args['annotate_peaks'])
    plotting_args['annotate_peaks'] = annotate_peaks
    annotate_precision = request.args.get('annotate_precision')
    plotting_args['annotate_precision'] = (
        default_plotting_args['annotate_precision']
        if not annotate_precision else int(annotate_precision))
    annotation_rotation = request.args.get('annotation_rotation')
    plotting_args['annotation_rotation'] = (
        default_plotting_args['annotation_rotation']
        if not annotation_rotation else float(annotation_rotation))
    max_intensity = request.args.get('max_intensity')
    if max_intensity:
        plotting_args['max_intensity'] = float(max_intensity) / 100
    else:
        plotting_args['max_intensity'] = (
            default_plotting_args['max_intensity_labeled']
            if any(annotate_peaks) else
            default_plotting_args['max_intensity_unlabeled'])
    return plotting_args


@app.route('/json/')
def peak_json():
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    # Return for JSON includes, peaks, n_peaks, and precursor_mz.
    spectrum_dict = {'peaks': [(float(mz), float(intensity)) for mz, intensity
                               in zip(spectrum.mz, spectrum.intensity)],
                     'n_peaks': len(spectrum.mz),
                     'precursor_mz': spectrum.precursor_mz}
    return flask.jsonify(spectrum_dict)


@app.route('/api/proxi/v0.1/spectra')
def peak_proxi_json():
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))

    spectrum_dict = {
        'intensities': [str(intensity) for intensity in spectrum.intensity],
        'mzs': [str(mz) for mz in spectrum.mz],
        'attributes': [
            {
                'accession': 'MS:1000744',
                'name': 'selected ion m/z',
                'value': str(spectrum.precursor_mz)
            },
            {
                'accession': 'MS:1000041',
                'name': 'precursor charge',
                'value': str(spectrum.precursor_charge)
            }
        ]
    }

    return flask.jsonify([spectrum_dict])


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
    return flask.render_template('500.html', error=error), 500
