import collections
import copy
import csv
import gc
import io
import json
from typing import Any, Dict, List, Optional, Tuple

import flask
import matplotlib
import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import qrcode
import requests_cache
import werkzeug
from spectrum_utils import plot as sup, spectrum as sus

import parsing

matplotlib.use('Agg')

requests_cache.install_cache('demo_cache', expire_after=300)

USI_SERVER = 'https://metabolomics-usi.ucsd.edu/'

default_plotting_args = {
    'width': 10.0,
    'height': 6.0,
    'max_intensity_unlabeled': 1.05,
    'max_intensity_labeled': 1.25,
    'max_intensity_mirror_labeled': 1.50,
    'grid': True,
    # List of peaks to annotate in the top/bottom spectrum.
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
    usi = flask.request.args.get('usi')
    plotting_args = _get_plotting_args(flask.request.args)
    spectrum, source_link = parsing.parse_usi(usi)
    spectrum = _prepare_spectrum(spectrum, **plotting_args)
    return flask.render_template(
        'spectrum.html',
        usi=usi,
        source_link=source_link,
        peaks=[_get_peaks(spectrum)],
        annotations=[spectrum.annotation.nonzero()[0].tolist()],
        plotting_args=plotting_args
    )


@blueprint.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plotting_args = _get_plotting_args(flask.request.args, mirror=True)
    spectrum1, source1 = parsing.parse_usi(usi1)
    spectrum2, source2 = parsing.parse_usi(usi2)
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    return flask.render_template(
        'mirror.html',
        usi1=usi1,
        usi2=usi2,
        source_link1=source1,
        source_link2=source2,
        peaks=[_get_peaks(spectrum1), _get_peaks(spectrum2)],
        annotations=[spectrum1.annotation.nonzero()[0].tolist(),
                     spectrum2.annotation.nonzero()[0].tolist()],
        plotting_args=plotting_args
    )


@blueprint.route('/png/')
def generate_png():
    plotting_args = _get_plotting_args(flask.request.args)
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    spectrum = _prepare_spectrum(spectrum, **plotting_args)
    buf = _generate_figure(spectrum, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/png/mirror/')
def generate_mirror_png():
    plotting_args = _get_plotting_args(flask.request.args, mirror=True)
    spectrum1, _ = parsing.parse_usi(flask.request.args.get('usi1'))
    spectrum2, _ = parsing.parse_usi(flask.request.args.get('usi2'))
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    buf = _generate_mirror_figure(spectrum1, spectrum2, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/svg/')
def generate_svg():
    plotting_args = _get_plotting_args(flask.request.args)
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    spectrum = _prepare_spectrum(spectrum, **plotting_args)
    buf = _generate_figure(spectrum, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


@blueprint.route('/svg/mirror/')
def generate_mirror_svg():
    plotting_args = _get_plotting_args(flask.request.args, mirror=True)
    spectrum1, _ = parsing.parse_usi(flask.request.args.get('usi1'))
    spectrum2, _ = parsing.parse_usi(flask.request.args.get('usi2'))
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    buf = _generate_mirror_figure(spectrum1, spectrum2, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


def _generate_figure(spectrum: sus.MsmsSpectrum, extension: str,
                     **kwargs: Any) -> io.BytesIO:
    """
    Generate a spectrum plot.

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum to be plotted.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the spectrum plot.
    """
    usi = spectrum.identifier

    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    sup.spectrum(
        spectrum, annotate_ions=kwargs['annotate_peaks'],
        annot_kws={'rotation': kwargs['annotation_rotation'], 'clip_on': True},
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
    subtitle = (f'Precursor $m$/$z$: '
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


def _generate_mirror_figure(spectrum_top: sus.MsmsSpectrum,
                            spectrum_bottom: sus.MsmsSpectrum,
                            extension: str, **kwargs: Any) -> io.BytesIO:
    """
    Generate a mirror plot of two spectra.

    Parameters
    ----------
    spectrum_top : sus.MsmsSpectrum
        The spectrum to be plotted at the top of the mirror plot.
    spectrum_bottom : sus.MsmsSpectrum
        The spectrum to be plotted at the bottom of the mirror plot.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the mirror plot.
    """
    usi1 = spectrum_top.identifier
    usi2 = spectrum_bottom.identifier

    fig, ax = plt.subplots(figsize=(kwargs['width'], kwargs['height']))

    # Determine cosine similarity and matching peaks.
    if kwargs['cosine']:
        # Initialize the annotations as unmatched.
        for annotation in spectrum_top.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'
        for annotation in spectrum_bottom.annotation:
            if annotation is not None:
                annotation.ion_type = 'unmatched'
        # Assign the matching peak annotations.
        similarity, peak_matches = cosine(
            spectrum_top, spectrum_bottom, kwargs['fragment_mz_tolerance'],
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

    # Colors for mirror plot peaks (subject to change).
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


def _prepare_spectrum(spectrum: sus.MsmsSpectrum, **kwargs: Any) \
        -> sus.MsmsSpectrum:
    """
    Process a spectrum for plotting.

    Processing includes restricting the m/z range, base peak normalizing
    peak intensities, and annotating spectrum peaks (either prespecified or
    using the heuristic approach in `_generate_labels`).
    These operations will not modify the original spectrum.

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum to be processed for plotting.
    kwargs : Any
        The processing and plotting settings.

    Returns
    -------
    sus.MsmsSpectrum
        The processed spectrum.
    """
    spectrum = copy.deepcopy(spectrum)
    spectrum.set_mz_range(kwargs['mz_min'], kwargs['mz_max'])
    spectrum.scale_intensity(max_intensity=1)

    # Initialize empty peak annotation list.
    if spectrum.annotation is None:
        spectrum.annotation = np.full_like(spectrum.mz, None, object)
    # Optionally set annotations.
    if kwargs['annotate_peaks']:
        if kwargs['annotate_peaks'] is True:
            kwargs['annotate_peaks'] = spectrum.mz[_generate_labels(
                spectrum, kwargs['annotate_threshold'])]
        for mz in kwargs['annotate_peaks']:
            spectrum.annotate_mz_fragment(
                mz, 0, kwargs['fragment_mz_tolerance'], 'Da',
                text=f'{mz:.{kwargs["annotate_precision"]}f}')

    return spectrum


def _generate_labels(spec: sus.MsmsSpectrum,
                     intensity_threshold: float = None,
                     num_labels: int = 20) -> List[int]:
    """
    Heuristic approach to label spectrum peaks.

    This will provide indices of the most intense peaks to be labeled, taking
    care not to label peaks that are too close to each other.

    Parameters
    ----------
    spec : sus.MsmsSpectrum
        The spectrum whose peaks are labeled.
    intensity_threshold : float
        The minimum intensity for peaks to be labeled.
    num_labels : int
        The maximum number of peaks that will be labeled. This won't always
        necessarily match the actual number of peaks that will be labeled.

    Returns
    -------
    List[int]
        Indices of the peaks that will be labeled.
    """
    if intensity_threshold is None:
        intensity_threshold = default_plotting_args['annotate_threshold']
    mz_exclusion_window = (spec.mz[-1] - spec.mz[0]) / num_labels

    # Annotate peaks in decreasing intensity order.
    labeled_i, order = [], np.argsort(spec.intensity)[::-1]
    for i, mz, intensity in zip(order, spec.mz[order], spec.intensity[order]):
        if intensity < intensity_threshold:
            break
        if not any(abs(mz - spec.mz[already_labeled_i]) <= mz_exclusion_window
                   for already_labeled_i in labeled_i):
            labeled_i.append(i)

    return labeled_i


def _get_peaks(spectrum: sus.MsmsSpectrum) -> List[Tuple[float, float]]:
    """
    Get the spectrum peaks as a list of tuples of (m/z, intensity).

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum whose peaks are returned.

    Returns
    -------
    List[Tuple[float, float]]
        A list with (m/z, intensity) tuples for all peaks in the given
        spectrum.
    """
    return [(float(mz), float(intensity))
            for mz, intensity in zip(spectrum.mz, spectrum.intensity)]


def _prepare_mirror_spectra(spectrum1: sus.MsmsSpectrum,
                            spectrum2: sus.MsmsSpectrum,
                            plotting_args: Dict[str, Any]) \
        -> Tuple[sus.MsmsSpectrum, sus.MsmsSpectrum]:
    """
    Process two spectra for plotting in a mirror plot.

    This function modifies the `plotting_args` dictionary so that it can be
    used to process both spectra separately with `_prepare_spectrum`.

    Parameters
    ----------
    spectrum1 : sus.MsmsSpectrum
        The first spectrum to be processed.
    spectrum2 : sus.MsmsSpectrum
        The second spectrum to be processed.
    plotting_args : Dict[str, Any]
        The processing and plotting settings.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, sus.MsmsSpectrum]
        Both processed spectra.
    """
    annotate_peaks = plotting_args['annotate_peaks']
    plotting_args['annotate_peaks'] = annotate_peaks[0]
    spectrum1 = _prepare_spectrum(spectrum1, **plotting_args)
    plotting_args['annotate_peaks'] = annotate_peaks[1]
    spectrum2 = _prepare_spectrum(spectrum2, **plotting_args)
    plotting_args['annotate_peaks'] = annotate_peaks
    return spectrum1, spectrum2


def _get_plotting_args(args: werkzeug.datastructures.ImmutableMultiDict,
                       mirror: bool = False) -> Dict[str, Any]:
    """
    Get the plotting configuration and spectrum processing options.

    Parameters
    ----------
    args : werkzeug.datastructures.ImmutableMultiDict
        The arguments from the plotting web requests.
    mirror : bool
        Flag indicating whether this is a mirror spectrum or not.

    Returns
    -------
    A dictionary with the plotting configuration and spectrum processing
    options.
    """
    plotting_args = {
        'width': args.get(
            'width', default_plotting_args['width'], type=float),
        'height': args.get(
            'height', default_plotting_args['height'], type=float),
        'mz_min': args.get('mz_min', None, type=float),
        'mz_max': args.get('mz_max', None, type=float),
        'grid': args.get(
            'grid', default_plotting_args['grid'],
            type=lambda grid: grid == 'true'),
        'annotate_peaks': args.get(
            'annotate_peaks', default_plotting_args['annotate_peaks'],
            type=lambda annotate_peaks_args: json.loads(annotate_peaks_args)),
        'annotate_precision': args.get(
            'annotate_precision', default_plotting_args['annotate_precision'],
            type=int),
        'annotate_threshold': default_plotting_args['annotate_threshold'],
        'annotation_rotation': args.get(
            'annotation_rotation',
            default_plotting_args['annotation_rotation'], type=float),
        'max_intensity': args.get('max_intensity', None, type=float),
        'cosine': args.get(
            'cosine', default_plotting_args['cosine'],
            type=lambda cos: cos if cos != 'off' else False),
        'fragment_mz_tolerance': args.get(
            'fragment_mz_tolerance',
            default_plotting_args['fragment_mz_tolerance'], type=float)
    }
    # Make sure that the figure size is valid.
    if plotting_args['width'] <= 0:
        plotting_args['width'] = default_plotting_args['width']
    if plotting_args['height'] <= 0:
        plotting_args['height'] = default_plotting_args['height']
    # Make sure that the mass range is valid.
    if plotting_args['mz_min'] is not None and plotting_args['mz_min'] <= 0:
        plotting_args['mz_min'] = None
    if plotting_args['mz_max'] is not None and plotting_args['mz_max'] <= 0:
        plotting_args['mz_max'] = None
    # Set maximum intensity based on the plot type.
    plotting_args['max_intensity'] = _get_max_intensity(
        plotting_args['max_intensity'], any(plotting_args['annotate_peaks']),
        mirror)
    # Set annotate_peaks for standard plots.
    if not mirror:
        plotting_args['annotate_peaks'] = plotting_args['annotate_peaks'][0]
    # Make sure that the annotation precision is valid.
    if plotting_args['annotate_precision'] < 0:
        plotting_args['annotate_precision'] = \
            default_plotting_args['annotate_precision']
    # Make sure that the fragment m/z tolerance is valid.
    if plotting_args['fragment_mz_tolerance'] < 0:
        plotting_args['fragment_mz_tolerance'] = \
            default_plotting_args['fragment_mz_tolerance']

    return plotting_args


def _get_max_intensity(max_intensity: Optional[float], annotate_peaks: bool,
                       mirror: bool) -> float:
    """
    Convert the maximum intensity from the web request.

    If no maximum intensity is specified the default value will be determined
    based on the type of plot (standard/mirror, unlabeled/labeled).

    Parameters
    ----------
    max_intensity : Optional[float]
        The maximum intensity specified in the web request.
    annotate_peaks : bool
        Flag indicating whether peaks are annotated or not.
    mirror : bool
        Flag indicating whether this is a standard plot or a mirror plot.

    Returns
    -------
    float
        The maximum intensity.
    """
    if max_intensity is not None:
        max_intensity = float(max_intensity) / 100
        # Make sure that the intensity range is sensible.
        if max_intensity > 0:
            return max_intensity
    # If the intensity is not specified or invalid, use a default value based
    # on plot type.
    if annotate_peaks:
        # Labeled (because peak annotations are provided) mirror or standard
        # plot.
        return (default_plotting_args['max_intensity_mirror_labeled'] if mirror
                else default_plotting_args['max_intensity_labeled'])
    else:
        # Unlabeled plot (no differentiation between standard and mirror).
        return default_plotting_args['max_intensity_unlabeled']


@blueprint.route('/json/')
def peak_json():
    try:
        spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
        result_dict = {
            'peaks': _get_peaks(spectrum),
            'n_peaks': len(spectrum.mz),
            'precursor_mz': spectrum.precursor_mz}
    except ValueError as e:
        result_dict = {'error': {'code': 404, 'message': str(e)}}
    return flask.jsonify(result_dict)


@blueprint.route('/api/proxi/v0.1/spectra')
def peak_proxi_json():
    try:
        usi = flask.request.args.get('usi')
        spectrum, _ = parsing.parse_usi(usi)
        result_dict = {
            'usi': usi,
            'status': 'READABLE',
            'mzs': spectrum.mz.tolist(),
            'intensities': spectrum.intensity.tolist(),
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
        result_dict = {'error': {'code': 404, 'message': str(e)}}
    return flask.jsonify([result_dict])


@blueprint.route('/csv/')
def peak_csv():
    spectrum, _ = parsing.parse_usi(flask.request.args.get('usi'))
    with io.StringIO() as csv_str:
        writer = csv.writer(csv_str)
        writer.writerow(['mz', 'intensity'])
        for mz, intensity in zip(spectrum.mz, spectrum.intensity):
            writer.writerow([mz, intensity])
        csv_bytes = io.BytesIO()
        csv_bytes.write(csv_str.getvalue().encode('utf-8'))
        csv_bytes.seek(0)
        return flask.send_file(
            csv_bytes, mimetype='text/csv', as_attachment=True,
            attachment_filename=f'{spectrum.identifier}.csv')


@blueprint.route('/qrcode/')
def generate_qr():
    if flask.request.args.get('mirror') != 'true':
        url = flask.request.url.replace('/qrcode/', '/spectrum/')
    else:
        url = flask.request.url.replace('/qrcode/?mirror=true&', '/mirror/?')
    qr_image = qrcode.make(url, box_size=2)
    qr_bytes = io.BytesIO()
    qr_image.save(qr_bytes, format='png')
    qr_bytes.seek(0)
    return flask.send_file(qr_bytes, 'image/png')


@blueprint.errorhandler(Exception)
def internal_error(error):
    return flask.render_template('500.html', error=error), 500
