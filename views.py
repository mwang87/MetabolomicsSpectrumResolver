import copy
import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple

import flask
import numpy as np
import qrcode
import urllib.parse
import redis
import werkzeug
from spectrum_utils import spectrum as sus

import drawing
import parsing
import similarity
import tasks
from error import UsiError


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
    plotting_args = get_plotting_args(flask.request.args)
    spectrum, source_link, splash_key = parse_usi(usi)
    spectrum = prepare_spectrum(spectrum, **plotting_args)
    return flask.render_template(
        'spectrum.html',
        usi=usi,
        usi_encoded=urllib.parse.quote_plus(usi),
        source_link=source_link,
        splash_key=splash_key,
        peaks=[get_peaks(spectrum)],
        annotations=[spectrum.annotation.nonzero()[0].tolist()],
        plotting_args=plotting_args
    )


@blueprint.route('/mirror/', methods=['GET'])
def render_mirror_spectrum():
    usi1 = flask.request.args.get('usi1')
    usi2 = flask.request.args.get('usi2')
    plotting_args = get_plotting_args(flask.request.args, mirror=True)
    spectrum1, source1, splash_key1 = parse_usi(usi1)
    spectrum2, source2, splash_key2 = parse_usi(usi2)
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    return flask.render_template(
        'mirror.html',
        usi1=usi1,
        usi2=usi2,
        usi1_encoded=urllib.parse.quote_plus(usi1),
        usi2_encoded=urllib.parse.quote_plus(usi2),
        source_link1=source1,
        source_link2=source2,
        splash_key1=splash_key1,
        splash_key2=splash_key2,
        peaks=[get_peaks(spectrum1), get_peaks(spectrum2)],
        annotations=[spectrum1.annotation.nonzero()[0].tolist(),
                     spectrum2.annotation.nonzero()[0].tolist()],
        plotting_args=plotting_args
    )


@blueprint.route('/png/')
def generate_png():
    plotting_args = get_plotting_args(flask.request.args)
    spectrum, _, _ = parse_usi(flask.request.args.get('usi'))
    spectrum = prepare_spectrum(spectrum, **plotting_args)
    buf = _generate_figure(spectrum, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/png/mirror/')
def generate_mirror_png():
    plotting_args = get_plotting_args(flask.request.args, mirror=True)
    spectrum1, _, _ = parse_usi(flask.request.args.get('usi1'))
    spectrum2, _, _ = parse_usi(flask.request.args.get('usi2'))
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    buf = _generate_mirror_figure(spectrum1, spectrum2, 'png', **plotting_args)
    return flask.send_file(buf, mimetype='image/png')


@blueprint.route('/svg/')
def generate_svg():
    plotting_args = get_plotting_args(flask.request.args)
    spectrum, _, _ = parse_usi(flask.request.args.get('usi'))
    spectrum = prepare_spectrum(spectrum, **plotting_args)
    buf = _generate_figure(spectrum, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


@blueprint.route('/svg/mirror/')
def generate_mirror_svg():
    plotting_args = get_plotting_args(flask.request.args, mirror=True)
    spectrum1, _, _ = parse_usi(flask.request.args.get('usi1'))
    spectrum2, _, _ = parse_usi(flask.request.args.get('usi2'))
    spectrum1, spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                   plotting_args)
    buf = _generate_mirror_figure(spectrum1, spectrum2, 'svg', **plotting_args)
    return flask.send_file(buf, mimetype='image/svg+xml')


def parse_usi(usi: str) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    The first attempt to parse the USI is via a Celery task. Alternatively, as
    a fallback option the USI can be parsed directly in this thread.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of the `MsmsSpectrum`, its source link, and its SPLASH.
        sus.MsmsSpectrum : spectrum object
    """
    # First attempt to schedule with Celery.
    try:
        return tasks.task_parse_usi.apply_async(args=(usi,)).get()
    except redis.exceptions.ConnectionError:
        # Fallback in case scheduling via Celery fails.
        # Mostly used for testing.
        return parsing.parse_usi(usi)


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
    try:
        return tasks.task_generate_figure.apply_async(
            args=(spectrum, extension), kwargs=kwargs).get()
    except redis.exceptions.ConnectionError:
        return drawing.generate_figure(spectrum, extension, **kwargs)


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
    try:
        return tasks.task_generate_mirror_figure.apply_async(
            args=(spectrum_top, spectrum_bottom, extension),
            kwargs=kwargs).get()
    except redis.exceptions.ConnectionError:
        return drawing.generate_mirror_figure(spectrum_top, spectrum_bottom,
                                              extension, **kwargs)


def prepare_spectrum(spectrum: sus.MsmsSpectrum, **kwargs: Any) \
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

    if spectrum.peptide is None:
        # Initialize empty peak annotation list.
        if spectrum.annotation is None:
            spectrum.annotation = np.full_like(spectrum.mz, None, object)
        # Optionally set annotations.
        if kwargs['annotate_peaks']:
            if kwargs['annotate_peaks'] is True:
                kwargs['annotate_peaks'] = spectrum.mz[_generate_labels(
                    spectrum, kwargs['annotate_threshold'])]
            annotate_peaks_valid = []
            for mz in kwargs['annotate_peaks']:
                try:
                    spectrum.annotate_mz_fragment(
                        mz, 0, kwargs['fragment_mz_tolerance'], 'Da',
                        text=f'{mz:.{kwargs["annotate_precision"]}f}')
                    annotate_peaks_valid.append(mz)
                except ValueError:
                    pass
            kwargs['annotate_peaks'] = annotate_peaks_valid
    else:
        # Here we have a peptide, and so we annotate it.
        spectrum = spectrum.annotate_peptide_fragments(
            kwargs['fragment_mz_tolerance'], 'Da', ion_types='aby',
            max_ion_charge=spectrum.precursor_charge)

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


def get_peaks(spectrum: sus.MsmsSpectrum) -> List[Tuple[float, float]]:
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
    spectrum1 = prepare_spectrum(spectrum1, **plotting_args)
    plotting_args['annotate_peaks'] = annotate_peaks[1]
    spectrum2 = prepare_spectrum(spectrum2, **plotting_args)
    plotting_args['annotate_peaks'] = annotate_peaks
    return spectrum1, spectrum2


def get_plotting_args(args: werkzeug.datastructures.ImmutableMultiDict,
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
            default_plotting_args['fragment_mz_tolerance'], type=float),
        'plot_title': args.get('plot_title', args.get('usi'))
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

    if plotting_args['width'] > 100:
        raise ValueError('Too large width')
    if plotting_args['height'] > 100:
        raise ValueError('Too large height')

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
        spectrum, _, splash_key = parse_usi(flask.request.args.get('usi'))
        result_dict = {
            'peaks': get_peaks(spectrum),
            'n_peaks': len(spectrum.mz),
            'precursor_mz': spectrum.precursor_mz,
            'splash': splash_key
        }
    except UsiError as e:
        result_dict = {'error': {'code': e.error_code, 'message': str(e)}}
    except ValueError as e:
        result_dict = {'error': {'code': 404, 'message': str(e)}}
    return flask.jsonify(result_dict)


@blueprint.route('/json/mirror/')
def mirror_json():
    try:
        usi1 = flask.request.args.get('usi1')
        usi2 = flask.request.args.get('usi2')

        plotting_args = get_plotting_args(flask.request.args, mirror=True)
        spectrum1, source1, splash_key1 = parse_usi(usi1)
        spectrum2, source2, splash_key2 = parse_usi(usi2)
        _spectrum1, _spectrum2 = _prepare_mirror_spectra(spectrum1, spectrum2,
                                                         plotting_args)
        score, peak_matches = similarity.cosine(
            _spectrum1, _spectrum2, plotting_args['fragment_mz_tolerance'],
            plotting_args['cosine'] == 'shifted')

        spectrum1_dict = {
            'peaks': get_peaks(spectrum1),
            'n_peaks': len(spectrum1.mz),
            'precursor_mz': spectrum1.precursor_mz,
            'splash': splash_key1
        }
        spectrum2_dict = {
            'peaks': get_peaks(spectrum2),
            'n_peaks': len(spectrum2.mz),
            'precursor_mz': spectrum2.precursor_mz,
            'splash': splash_key2
        }
        result_dict = {'spectrum1': spectrum1_dict,
                       'spectrum2': spectrum2_dict,
                       'cosine': score,
                       'n_peak_matches': len(peak_matches),
                       'peak_matches': peak_matches}

    except UsiError as e:
        result_dict = {'error': {'code': e.error_code, 'message': str(e)}}
    except ValueError as e:
        result_dict = {'error': {'code': 404, 'message': str(e)}}
    return flask.jsonify(result_dict)


@blueprint.route('/proxi/v0.1/spectra')
def peak_proxi_json():
    try:
        usi = flask.request.args.get('usi')
        spectrum, _, splash_key = parse_usi(usi)
        result_dict = {
            'usi': usi,
            'status': 'READABLE',
            'mzs': spectrum.mz.tolist(),
            'intensities': spectrum.intensity.tolist(),
            'attributes': [
                {
                    'accession': 'MS:1000744',
                    'name': 'selected ion m/z',
                    'value': str(spectrum.precursor_mz)
                },
                {
                    'accession': 'MS:1000041',
                    'name': 'charge state',
                    'value': str(spectrum.precursor_charge)
                }
            ]
        }
        if splash_key is not None:
            result_dict['attributes'].append({
                'accession': 'MS:1002599', 'name': 'splash key',
                'value': splash_key})
    except UsiError as e:
        result_dict = {'error': {'code': e.error_code, 'message': str(e)}}
    except ValueError as e:
        result_dict = {'error': {'code': 404, 'message': str(e)}}
    return flask.jsonify([result_dict])


@blueprint.route('/csv/')
def peak_csv():
    spectrum, _, _ = parse_usi(flask.request.args.get('usi'))
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
def render_error(error):
    if type(error) == UsiError:
        error_code = error.error_code
    else:
        error_code = 500
    if hasattr(error, 'message'):
        error_message = error.message
    else:
        error_message = 'RunTime Server Error'

    return (flask.render_template('error.html', error=error_message),
            error_code)
