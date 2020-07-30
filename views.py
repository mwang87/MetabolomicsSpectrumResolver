import collections
import copy
import csv
import gc
import io
import json
from typing import List, Tuple

import flask
import matplotlib
import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import qrcode
import requests_cache
from spectrum_utils import plot as sup, spectrum as sus

import parsing

matplotlib.use('Agg')

requests_cache.install_cache('demo_cache', expire_after=300)

USI_SERVER = 'https://metabolomics-usi.ucsd.edu/'

default_plotting_args = {
    'width': 10,
    'height': 6,
    'max_intensity_unlabeled': 1.05,
    'max_intensity_labeled': 1.25,
    'max_intensity_mirror_labeled': 1.50,
    'grid': True,
    # List of peaks to annotate in the top/bottom
    # spectrum.
    'annotate_peaks': [True, True],
    'annotate_threshold': 0.1,
    'annotate_precision': 4,
    'annotation_rotation': 90,
    'cosine': 'standard',
    'fragment_mz_tolerance': 0.02
}

blueprint = flask.Blueprint('ui', __name__)


SpectrumTuple = collections.namedtuple(
    'SpectrumTuple', ['precursor_mz', 'precursor_charge', 'mz', 'intensity'])


@blueprint.route('/', methods=['GET'])
def render_homepage():
    return flask.render_template('homepage.html')


@blueprint.route('/contributors', methods=['GET'])
def render_contributors():
    return flask.render_template('contributors.html')


@blueprint.route('/heartbeat', methods=['GET'])
def render_heartbeat():
    return json.dumps({'status': 'success'})


@blueprint.route('/spectrum/', methods=['GET'])
def render_spectrum():
    spectrum, source_link = parsing.parse_usi(flask.request.args.get('usi'))
    spectrum = copy.deepcopy(spectrum)
    spectrum.scale_intensity(max_intensity=1)
    return flask.render_template(
        'spectrum.html',
        usi=flask.request.args.get('usi'),
        source_link=source_link,
        peaks=[_get_peaks(spectrum)],
        annotations=[_generate_labels(spectrum)],
        plotting_args=_get_plotting_args(flask.request)
    )


@blueprint.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    spectrum1, source1 = parsing.parse_usi(flask.request.args.get('usi1'))
    spectrum1 = copy.deepcopy(spectrum1)
    spectrum1.scale_intensity(max_intensity=1)
    spectrum2, source2 = parsing.parse_usi(flask.request.args.get('usi2'))
    spectrum2 = copy.deepcopy(spectrum2)
    spectrum2.scale_intensity(max_intensity=1)
    return flask.render_template(
        'mirror.html',
        usi1=flask.request.args.get('usi1'),
        usi2=flask.request.args.get('usi2'),
        source_link1=source1,
        source_link2=source2,
        peaks=[_get_peaks(spectrum1), _get_peaks(spectrum2)],
        annotations=[_generate_labels(spectrum1), _generate_labels(spectrum2)],
        plotting_args=_get_plotting_args(flask.request)
    )


@blueprint.route('/png/')
def generate_png():
    usi = flask.request.args.get('usi')
    plotting_args = _get_plotting_args(flask.request)
    buf = _generate_figure(usi, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/png/mirror/')
def generate_mirror_png():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plotting_args = _get_plotting_args(flask.request, mirror=True)
    buf = _generate_mirror_figure(usi1, usi2, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/svg/')
def generate_svg():
    usi = flask.request.args.get('usi')
    plotting_args = _get_plotting_args(flask.request)
    buf = _generate_figure(usi, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


@blueprint.route('/svg/mirror/')
def generate_mirror_svg():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plotting_args = _get_plotting_args(flask.request, mirror=True)
    buf = _generate_mirror_figure(usi1, usi2, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


def _generate_figure(usi: str, extension: str, **kwargs) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    kwargs['annotate_peaks'] = kwargs['annotate_peaks'][0]
    spectrum = _prepare_spectrum(usi, **kwargs)
    sup.spectrum(
        spectrum,
        annotate_ions=kwargs['annotate_peaks'],
        annot_kws={'rotation': kwargs['annotation_rotation'], 'clip_on': True},
        grid=kwargs['grid'], ax=ax,
    )

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

    buf = io.BytesIO()
    plt.savefig(buf, bbox_inches='tight', format=extension)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    gc.collect()

    return buf


def _generate_mirror_figure(usi1: str, usi2: str, extension: str, **kwargs) \
        -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    annotate_peaks = kwargs['annotate_peaks']
    kwargs['annotate_peaks'] = annotate_peaks[0]
    spectrum_top = _prepare_spectrum(usi1, **kwargs)
    kwargs['annotate_peaks'] = annotate_peaks[1]
    spectrum_bottom = _prepare_spectrum(usi2, **kwargs)

    fragment_mz_tolerance = kwargs['fragment_mz_tolerance']

    if kwargs['cosine']:
        # Initialize the annotations as unmatched.
        if spectrum_top.annotation is None:
            spectrum_top.annotation = np.full_like(
                spectrum_top.mz, None, object)
        if spectrum_bottom.annotation is None:
            spectrum_bottom.annotation = np.full_like(
                spectrum_bottom.mz, None, object)
        for annotation in spectrum_top.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'
        for annotation in spectrum_bottom.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'
        # Assign the matching peak annotations.
        similarity, peak_matches = cosine(
            spectrum_top, spectrum_bottom, fragment_mz_tolerance,
            kwargs['cosine'] == 'shifted')
        for top_i, bottom_i in peak_matches:
            if spectrum_top.annotation[top_i] is None:
                spectrum_top.annotation[top_i] = sus.FragmentAnnotation(
                    0, spectrum_top.mz[top_i], '')
            spectrum_top.annotation[top_i].ion_type = 'top'
            if spectrum_bottom.annotation[bottom_i] is None:
                spectrum_bottom.annotation[bottom_i] = sus.FragmentAnnotation(
                    0, spectrum_bottom.mz[bottom_i], '')
            spectrum_bottom.annotation[bottom_i].ion_type = 'bottom'
    else:
        similarity = 0

    # Colors for mirror plot peaks, subject to change.
    sup.colors['top'] = '#212121'
    sup.colors['bottom'] = '#388E3C'
    sup.colors['unmatched'] = 'darkgray'

    sup.mirror(spectrum_top, spectrum_bottom,
               {'annotate_ions': kwargs['annotate_peaks'],
                'annot_kws': {'rotation': kwargs['annotation_rotation'],
                              'clip_on': True},
                'grid': kwargs['grid']}, ax=ax)

    ax.set_xlim(kwargs['mz_min'], kwargs['mz_max'])
    ax.set_ylim(-kwargs['max_intensity'], kwargs['max_intensity'])

    if not kwargs['grid']:
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

    text_y = 1.2 if kwargs['cosine'] else 1.15
    for usi, spec, loc in zip([usi1, usi2], [spectrum_top, spectrum_bottom],
                              ['Top', 'Bottom']):
        title = ax.text(0.5, text_y, f'{loc}: {usi}',
                        horizontalalignment='center',
                        verticalalignment='bottom',
                        fontsize='x-large',
                        fontweight='bold',
                        transform=ax.transAxes)
        title.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
        text_y -= 0.04
        subtitle = (
            f'Precursor $m$/$z$: '
            f'{spec.precursor_mz:.{kwargs["annotate_precision"]}f} '
            if spec.precursor_mz > 0 else '')
        subtitle += f'Charge: {spec.precursor_charge}'
        subtitle = ax.text(0.5, text_y, subtitle, horizontalalignment='center',
                           verticalalignment='bottom', fontsize='large',
                           transform=ax.transAxes)
        subtitle.set_url(f'{USI_SERVER}mirror/?usi1={usi1}&usi2={usi2}')
        text_y -= 0.06

    if kwargs['cosine']:
        subtitle_score = f'Cosine similarity = {similarity:.4f}'
        ax.text(0.5, text_y, subtitle_score, horizontalalignment='center',
                verticalalignment='bottom', fontsize='x-large',
                fontweight='bold', transform=ax.transAxes)

    buf = io.BytesIO()
    plt.savefig(buf, bbox_inches='tight', format=extension)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    gc.collect()

    return buf


def cosine(spectrum1: sus.MsmsSpectrum, spectrum2: sus.MsmsSpectrum,
           fragment_mz_tolerance: float, allow_shift: bool) \
        -> Tuple[float, List[Tuple[int, int]]]:
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
    allow_shift : bool
        Boolean flag indicating whether to allow peak shifts or not.

    Returns
    -------
    Tuple[float, List[Tuple[int, int]]]
        A tuple consisting of (i) the cosine similarity between both spectra,
        and (ii) the indexes of matching peaks in both spectra.
    """
    spec_tup1 = SpectrumTuple(
        spectrum1.precursor_mz, spectrum1.precursor_charge, spectrum1.mz,
        np.copy(spectrum1.intensity) / np.linalg.norm(spectrum1.intensity))
    spec_tup2 = SpectrumTuple(
        spectrum2.precursor_mz, spectrum2.precursor_charge, spectrum2.mz,
        np.copy(spectrum2.intensity) / np.linalg.norm(spectrum2.intensity))
    return _cosine(spec_tup1, spec_tup2, fragment_mz_tolerance, allow_shift)


@nb.njit
def _cosine(spec: SpectrumTuple, spec_other: SpectrumTuple,
            fragment_mz_tolerance: float, allow_shift: bool) \
        -> Tuple[float, List[Tuple[int, int]]]:
    """
    Compute the cosine similarity between the given spectra.

    Parameters
    ----------
    spec : SpectrumTuple
        Numba-compatible tuple containing information from the first spectrum.
    spec_other : SpectrumTuple
        Numba-compatible tuple containing information from the second spectrum.
    fragment_mz_tolerance : float
        The fragment m/z tolerance used to match peaks in both spectra with
        each other.
    allow_shift : bool
        Boolean flag indicating whether to allow peak shifts or not.

    Returns
    -------
    Tuple[float, List[Tuple[int, int]]]
        A tuple consisting of (i) the cosine similarity between both spectra,
        and (ii) the indexes of matching peaks in both spectra.
    """
    # Find the matching peaks between both spectra, optionally allowing for
    # shifted peaks.
    # Candidate peak indices depend on whether we allow shifts
    # (check all shifted peaks as well) or not.
    # Account for unknown precursor charge (default: 1).
    precursor_charge = max(spec.precursor_charge, 1)
    precursor_mass_diff = ((spec.precursor_mz - spec_other.precursor_mz)
                           * precursor_charge)
    # Only take peak shifts into account if the mass difference is relevant.
    num_shifts = 1
    if allow_shift and abs(precursor_mass_diff) >= fragment_mz_tolerance:
        num_shifts += precursor_charge
    other_peak_index = np.zeros(num_shifts, np.uint16)
    mass_diff = np.zeros(num_shifts, np.float32)
    for charge in range(1, num_shifts):
        mass_diff[charge] = precursor_mass_diff / charge

    # Find the matching peaks between both spectra.
    peak_match_scores, peak_match_idx = [], []
    for peak_index, (peak_mz, peak_intensity) in enumerate(zip(
            spec.mz, spec.intensity)):
        # Advance while there is an excessive mass difference.
        for cpi in range(num_shifts):
            while (other_peak_index[cpi] < len(spec_other.mz) - 1 and
                   (peak_mz - fragment_mz_tolerance >
                    spec_other.mz[other_peak_index[cpi]] + mass_diff[cpi])):
                other_peak_index[cpi] += 1
        # Match the peaks within the fragment mass window if possible.
        for cpi in range(num_shifts):
            index = 0
            other_peak_i = other_peak_index[cpi] + index
            while (other_peak_i < len(spec_other.mz) and
                   abs(peak_mz - (spec_other.mz[other_peak_i]
                       + mass_diff[cpi])) <= fragment_mz_tolerance):
                peak_match_scores.append(
                    peak_intensity * spec_other.intensity[other_peak_i])
                peak_match_idx.append((peak_index, other_peak_i))
                index += 1
                other_peak_i = other_peak_index[cpi] + index

    score, peak_matches = 0., []
    if len(peak_match_scores) > 0:
        # Use the most prominent peak matches to compute the score (sort in
        # descending order).
        peak_match_scores_arr = np.asarray(peak_match_scores)
        peak_match_order = np.argsort(peak_match_scores_arr)[::-1]
        peak_match_scores_arr = peak_match_scores_arr[peak_match_order]
        peak_match_idx_arr = np.asarray(peak_match_idx)[peak_match_order]
        peaks_used, other_peaks_used = set(), set()
        for peak_match_score, peak_i, other_peak_i in zip(
                peak_match_scores_arr, peak_match_idx_arr[:, 0],
                peak_match_idx_arr[:, 1]):
            if (peak_i not in peaks_used
                    and other_peak_i not in other_peaks_used):
                score += peak_match_score
                # Save the matched peaks.
                peak_matches.append((peak_i, other_peak_i))
                # Make sure these peaks are not used anymore.
                peaks_used.add(peak_i)
                other_peaks_used.add(other_peak_i)

    return score, peak_matches


def _prepare_spectrum(usi: str, **kwargs) -> sus.MsmsSpectrum:
    spectrum, _ = parsing.parse_usi(usi)
    spectrum = copy.deepcopy(spectrum)
    spectrum.scale_intensity(max_intensity=1)

    if kwargs['annotate_peaks']:
        if kwargs['annotate_peaks'] is True:
            kwargs['annotate_peaks'] = spectrum.mz[_generate_labels(spectrum)]
        for mz in kwargs['annotate_peaks']:
            t = f'{mz:.{kwargs["annotate_precision"]}f}'
            spectrum.annotate_mz_fragment(
                mz, 0, kwargs['fragment_mz_tolerance'], 'Da', text=t)

    spectrum.set_mz_range(kwargs['mz_min'], kwargs['mz_max'])
    spectrum.scale_intensity(max_intensity=1)

    return spectrum


def _get_peaks(spectrum: sus.MsmsSpectrum) -> List[Tuple[float, float]]:
    return [
        (float(mz), float(intensity))
        for mz, intensity in zip(spectrum.mz, spectrum.intensity)
    ]


def _generate_labels(spec, intensity_threshold=None):
    if intensity_threshold is None:
        intensity_threshold = default_plotting_args['annotate_threshold']
    mz_exclusion_window = (spec.mz[-1] - spec.mz[0]) / 20  # Max 20 labels.

    # Annotate peaks in decreasing intensity order.
    labeled_i, order = [], np.argsort(spec.intensity)[::-1]
    for i, mz, intensity in zip(order, spec.mz[order], spec.intensity[order]):
        if intensity < intensity_threshold:
            break
        if not any(
            abs(mz - spec.mz[already_labeled_i]) <= mz_exclusion_window
            for already_labeled_i in labeled_i
        ):
            labeled_i.append(i)

    return labeled_i


def _get_plotting_args(request, mirror=False):
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
    # Explicitly specified maximum intensity.
    if max_intensity:
        plotting_args['max_intensity'] = float(max_intensity) / 100
    # Default labeled maximum intensity.
    elif any(annotate_peaks):
        # Default mirror plot labeled maximum intensity.
        if mirror:
            plotting_args['max_intensity'] = \
                default_plotting_args['max_intensity_mirror_labeled']
        # Default standard plot labeled maximum intensity.
        else:
            plotting_args['max_intensity'] = \
                default_plotting_args['max_intensity_labeled']
    # Default unlabeled maximum intensity.
    else:
        plotting_args['max_intensity'] = \
            default_plotting_args['max_intensity_unlabeled']
    cosine_type = request.args.get('cosine')
    plotting_args['cosine'] = (default_plotting_args['cosine']
                               if cosine_type is None else cosine_type)
    if plotting_args['cosine'] == 'off':
        plotting_args['cosine'] = False
    fragment_mz_tolerance = request.args.get('fragment_mz_tolerance')
    plotting_args['fragment_mz_tolerance'] = (
        default_plotting_args['fragment_mz_tolerance']
        if fragment_mz_tolerance is None else float(fragment_mz_tolerance))

    return plotting_args


@blueprint.route('/json/')
def peak_json():
    try:
        spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
        # Return for JSON includes, peaks, n_peaks, and precursor_mz.
        result_dict = {
            'peaks': _get_peaks(spectrum),
            'n_peaks': len(spectrum.mz),
            'precursor_mz': spectrum.precursor_mz}
    except ValueError as e:
        result_dict = {'error': {'code': 404,
                                 'message': str(e)}}
    return flask.jsonify(result_dict)


@blueprint.route('/api/proxi/v0.1/spectra')
def peak_proxi_json():
    try:
        spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
        result_dict = {
            'intensities': spectrum.intensity.tolist(),
            'mzs': spectrum.mz.tolist(),
            'attributes': [
                {
                    'accession': 'MS:1000744',
                    'name': 'selected ion m/z',
                    'value': float(spectrum.precursor_mz)
                },
                {
                    'accession': 'MS:1000041',
                    'name': 'charge state',
                    'value': int(spectrum.precursor_charge)
                }
            ]
        }
    except ValueError as e:
        result_dict = {'error': {'code': 404,
                                 'message': str(e)}}

    return flask.jsonify([result_dict])


@blueprint.route('/csv/')
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


@blueprint.route('/qrcode/')
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


@blueprint.errorhandler(Exception)
def internal_error(error):
    return flask.render_template('500.html', error=error), 500
