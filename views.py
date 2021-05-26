import copy
import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.parse

import flask
import numpy as np
import qrcode
from spectrum_utils import spectrum as sus

import similarity
import tasks
from error import UsiError


default_drawing_controls = {
    "width": 10,
    "height": 6,
    "mz_min": None,
    "mz_max": None,
    "max_intensity_unlabeled": 105,
    "max_intensity_labeled": 125,
    "max_intensity_mirror_labeled": 150,
    "annotate_precision": 4,
    "annotation_rotation": 90,
    "cosine": "standard",
    "fragment_mz_tolerance": 0.02,
    "grid": "True",
    # List of peaks to annotate in the first/second spectrum.
    "annotate_peaks": [True, True],
    "annotate_threshold": 0.1,
}

blueprint = flask.Blueprint("ui", __name__)


@blueprint.route("/", methods=["GET"])
def render_homepage():
    return flask.render_template("homepage.html")


@blueprint.route("/contributors", methods=["GET"])
def render_contributors():
    return flask.render_template("contributors.html")


@blueprint.route("/heartbeat", methods=["GET"])
def render_heartbeat():
    return json.dumps({"status": "success"})

# Forwarding some urls
@blueprint.route("/spectrum/", methods=["GET"])
def spectrum_forward():
    params_string = urllib.parse.urlencode(flask.request.args.to_dict(), quote_via=urllib.parse.quote)
    return flask.redirect("/dashinterface?{}".format(params_string), code=302)

@blueprint.route("/mirror/", methods=["GET"])
def mirror_forward():
    params_string = urllib.parse.urlencode(flask.request.args.to_dict(), quote_via=urllib.parse.quote)
    return flask.redirect("/dashinterface?{}".format(params_string), code=302)

@blueprint.route("/png/")
def generate_png():
    # Making sure annotate peaks is a list
    request_arguments = flask.request.args.to_dict()
    if "annotate_peaks" in request_arguments:
        request_arguments["annotate_peaks"] = json.loads(request_arguments["annotate_peaks"])

    drawing_controls = get_drawing_controls(**request_arguments)
    if drawing_controls["annotate_peaks"] is not None:
        drawing_controls["annotate_peaks"] = drawing_controls["annotate_peaks"][0]

    # noinspection PyTypeChecker
    spectrum = prepare_spectrum(
        tasks.parse_usi(drawing_controls["usi1"])[0], **drawing_controls
    )
    buf = tasks.generate_figure(spectrum, "png", **drawing_controls)
    return flask.send_file(buf, mimetype="image/png")


@blueprint.route("/png/mirror/")
def generate_mirror_png():
    # Making sure annotate peaks is a list
    request_arguments = flask.request.args.to_dict()
    if "annotate_peaks" in request_arguments:
        request_arguments["annotate_peaks"] = json.loads(request_arguments["annotate_peaks"])

    drawing_controls = get_drawing_controls(
        **request_arguments, mirror=True
    )
    # noinspection PyTypeChecker
    spectrum1, spectrum2 = _prepare_mirror_spectra(
        tasks.parse_usi(drawing_controls["usi1"])[0],
        tasks.parse_usi(drawing_controls["usi2"])[0],
        **drawing_controls,
    )
    buf = tasks.generate_mirror_figure(
        spectrum1, spectrum2, "png", **drawing_controls
    )
    return flask.send_file(buf, mimetype="image/png")


@blueprint.route("/svg/")
def generate_svg():
    # Making sure annotate peaks is a list
    request_arguments = flask.request.args.to_dict()
    if "annotate_peaks" in request_arguments:
        request_arguments["annotate_peaks"] = json.loads(request_arguments["annotate_peaks"])

    drawing_controls = get_drawing_controls(**request_arguments)
    if drawing_controls["annotate_peaks"] is not None:
        drawing_controls["annotate_peaks"] = drawing_controls["annotate_peaks"][0]
    
    # noinspection PyTypeChecker
    spectrum = prepare_spectrum(
        tasks.parse_usi(drawing_controls["usi1"])[0], **drawing_controls
    )

    buf = tasks.generate_figure(spectrum, "svg", **drawing_controls)
    return flask.send_file(buf, mimetype="image/svg+xml")


@blueprint.route("/svg/mirror/")
def generate_mirror_svg():
    # Making sure annotate peaks is a list
    request_arguments = flask.request.args.to_dict()
    if "annotate_peaks" in request_arguments:
        request_arguments["annotate_peaks"] = json.loads(request_arguments["annotate_peaks"])

    drawing_controls = get_drawing_controls(
        **request_arguments, mirror=True
    )
    # noinspection PyTypeChecker
    spectrum1, spectrum2 = _prepare_mirror_spectra(
        tasks.parse_usi(drawing_controls["usi1"])[0],
        tasks.parse_usi(drawing_controls["usi2"])[0],
        **drawing_controls,
    )
    buf = tasks.generate_mirror_figure(
        spectrum1, spectrum2, "svg", **drawing_controls
    )
    return flask.send_file(buf, mimetype="image/svg+xml")


def get_drawing_controls(
    *,
    usi1: str,
    usi2: str = "",
    width: float = default_drawing_controls["width"],
    height: float = default_drawing_controls["height"],
    mz_min: float = default_drawing_controls["mz_min"],
    mz_max: float = default_drawing_controls["mz_max"],
    max_intensity: int = default_drawing_controls["max_intensity_unlabeled"],
    annotate_precision: int = default_drawing_controls["annotate_precision"],
    annotation_rotation: int = default_drawing_controls["annotation_rotation"],
    cosine: str = default_drawing_controls["cosine"],
    fragment_mz_tolerance: Optional[float] = None,
    grid: bool = default_drawing_controls["grid"],
    annotate_peaks: List[Union[bool, List[float]]] = None,
    mirror: Optional[bool] = False,
) -> Dict[str, Any]:
    """
    Get the plotting configuration and spectrum processing options.

    Parameters
    ----------
    usi1 : str
        The first USI input.
    usi2 : str
        The second USI input (optional; if specified a mirror plot will be
        drawn).
    width : float
        The figure width.
    height : float
        The figure height.
    mz_min : float
        The minimum m/z value.
    mz_max : float
        The maximum m/z value.
    max_intensity : float
        The maximum intensity value.
    annotate_precision : int
        The m/z precision of peak labels.
    annotation_rotation : int
        The angle of peak labels.
    cosine : str
        The type of cosine score.
    fragment_mz_tolerance : float
        The fragment m/z tolerance.
    grid : bool
        Whether to display the grid.
    annotate_peaks: List[Union[bool, List[float]]] = None,
        M/z values of the peaks in both spectra that should be labeled.
    mirror : bool
        Flag indicating whether this is a mirror spectrum or not.

    Returns
    -------
    A dictionary with the configuration for processing spectra and generating
    figures.
    """
    drawing_controls = {"usi1": usi1, "usi2": usi2}
    # If the drawing controls have an incorrect value and are missing, their
    # default will be used instead.
    try:
        drawing_controls["width"] = float(width)
        if drawing_controls["width"] <= 0 or drawing_controls["width"] > 100:
            drawing_controls["width"] = default_drawing_controls["width"]
    except (TypeError, ValueError):
        drawing_controls["width"] = default_drawing_controls["width"]
    try:
        drawing_controls["height"] = float(height)
        if drawing_controls["height"] <= 0 or drawing_controls["height"] > 100:
            drawing_controls["height"] = default_drawing_controls["height"]
    except (TypeError, ValueError):
        drawing_controls["height"] = default_drawing_controls["height"]
    try:
        drawing_controls["mz_min"] = float(mz_min)
        if drawing_controls["mz_min"] <= 0:
            drawing_controls["mz_min"] = None
    except (TypeError, ValueError):
        drawing_controls["mz_min"] = default_drawing_controls["mz_min"]
    try:
        drawing_controls["mz_max"] = float(mz_max)
        if drawing_controls["mz_max"] <= 0:
            drawing_controls["mz_max"] = None
    except (TypeError, ValueError):
        drawing_controls["mz_max"] = default_drawing_controls["mz_max"]
    try:
        drawing_controls["max_intensity"] = int(max_intensity)
        if drawing_controls["max_intensity"] <= 0:
            drawing_controls["max_intensity"] = None
    except (TypeError, ValueError):
        drawing_controls["max_intensity"] = None
    try:
        drawing_controls["annotate_precision"] = int(annotate_precision)
        if drawing_controls["annotate_precision"] < 0:
            drawing_controls["annotate_precision"] = default_drawing_controls[
                "annotate_precision"
            ]
    except (TypeError, ValueError):
        drawing_controls["annotate_precision"] = default_drawing_controls[
            "annotate_precision"
        ]
    try:
        drawing_controls["annotation_rotation"] = int(annotation_rotation)
    except (TypeError, ValueError):
        drawing_controls["annotation_rotation"] = default_drawing_controls[
            "annotation_rotation"
        ]
    drawing_controls["cosine"] = cosine
    try:
        drawing_controls["fragment_mz_tolerance"] = float(
            fragment_mz_tolerance
        )
        if drawing_controls["fragment_mz_tolerance"] < 0:
            drawing_controls[
                "fragment_mz_tolerance"
            ] = default_drawing_controls["fragment_mz_tolerance"]
    except (TypeError, ValueError):
        drawing_controls["fragment_mz_tolerance"] = default_drawing_controls[
            "fragment_mz_tolerance"
        ]
    drawing_controls["grid"] = grid == "True"
    drawing_controls["annotate_peaks"] = annotate_peaks
    if drawing_controls["max_intensity"] is None:
        if annotate_peaks is not None and any(annotate_peaks):
            # Labeled (because peak annotations are provided) standard or
            # mirror plot.
            drawing_controls["max_intensity"] = (
                default_drawing_controls["max_intensity_labeled"]
                if not mirror
                else default_drawing_controls["max_intensity_mirror_labeled"]
            )
        else:
            # Unlabeled plot (no difference between standard and mirror).
            drawing_controls["max_intensity"] = default_drawing_controls[
                "max_intensity_labeled"
            ] if not mirror else default_drawing_controls["max_intensity_mirror_labeled"]

    return drawing_controls


def prepare_spectrum(
    spectrum: sus.MsmsSpectrum, **kwargs: Any
) -> sus.MsmsSpectrum:
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
    spectrum.set_mz_range(kwargs["mz_min"], kwargs["mz_max"])
    spectrum.scale_intensity(max_intensity=1)

    # Annotate spectrum peaks.
    if spectrum.peptide is not None:
        # Annotate canonical peptide fragments.
        spectrum = spectrum.annotate_peptide_fragments(
            kwargs["fragment_mz_tolerance"],
            "Da",
            ion_types="aby",
            max_ion_charge=spectrum.precursor_charge,
        )
        # TODO: Explicitly specified peaks should additionally be labeled with
        #       their m/z values.
    else:
        # Annotate peaks with their m/z values.
        if spectrum.annotation is None:
            # noinspection PyTypeChecker
            spectrum.annotation = np.full_like(spectrum.mz, None, object)
        # Optionally set annotations.
        if kwargs["annotate_peaks"]:
            if kwargs["annotate_peaks"] is True:
                kwargs["annotate_peaks"] = spectrum.mz[
                    _generate_labels(spectrum)
                ]
            annotate_peaks_valid = []
            for mz in kwargs["annotate_peaks"]:
                try:
                    spectrum.annotate_mz_fragment(
                        mz,
                        0,
                        0.001,
                        "Da",
                        text=f'{mz:.{kwargs["annotate_precision"]}f}',
                    )
                    annotate_peaks_valid.append(mz)
                except ValueError:
                    pass
            kwargs["annotate_peaks"] = annotate_peaks_valid

    return spectrum


def _generate_labels(
    spec: sus.MsmsSpectrum,
    intensity_threshold: float = None,
    num_labels: int = 20,
) -> List[int]:
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
        intensity_threshold = default_drawing_controls["annotate_threshold"]
    mz_exclusion_window = (spec.mz[-1] - spec.mz[0]) / num_labels

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


def _prepare_mirror_spectra(
    spectrum1: sus.MsmsSpectrum, spectrum2: sus.MsmsSpectrum, **kwargs: Any,
) -> Tuple[sus.MsmsSpectrum, sus.MsmsSpectrum]:
    """
    Process two spectra for plotting in a mirror plot.

    This function modifies the `plotting_args` dictionary so that it can be
    used to process both spectra separately with `_prepare_spectrum`.

    Parameters
    ----------
    spectrum1 : sus.MsmsSpectrum
        The first spectrum to be processed for plotting.
    spectrum2 : sus.MsmsSpectrum
        The second spectrum to be processed for plotting.
    kwargs : Any
        The processing and plotting settings.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, sus.MsmsSpectrum]
        Both processed spectra.
    """
    annotate_peaks = kwargs["annotate_peaks"]
    if annotate_peaks is not None:
        kwargs["annotate_peaks"] = annotate_peaks[0]
    spectrum1 = prepare_spectrum(spectrum1, **kwargs)
    if annotate_peaks is not None:
        kwargs["annotate_peaks"] = annotate_peaks[1]
    spectrum2 = prepare_spectrum(spectrum2, **kwargs)
    kwargs["annotate_peaks"] = annotate_peaks
    return spectrum1, spectrum2


@blueprint.route("/json/")
def peak_json():
    try:
        spectrum, _, splash_key = tasks.parse_usi(
            flask.request.args.get("usi1")
        )
        peaks = list(zip(spectrum.mz, spectrum.intensity))
        peaks = [[float(peak[0]), float(peak[1])] for peak in peaks]
        result_dict = {
            "peaks": peaks,
            "n_peaks": len(spectrum.mz),
            "precursor_mz": float(spectrum.precursor_mz),
            "precursor_charge": int(spectrum.precursor_charge),
            "splash": splash_key,
        }
        status = 200
    except UsiError as e:
        result_dict = {"error": {"code": e.error_code, "message": str(e)}}
        status = e.error_code
    except ValueError as e:
        result_dict = {"error": {"code": 404, "message": str(e)}}
        status = 404
    return flask.jsonify(result_dict), status


@blueprint.route("/json/mirror/")
def mirror_json():
    try:
        drawing_controls = get_drawing_controls(
            **flask.request.args.to_dict(), mirror=True
        )
        spectrum1, source1, splash_key1 = tasks.parse_usi(
            drawing_controls["usi1"]
        )
        spectrum2, source2, splash_key2 = tasks.parse_usi(
            drawing_controls["usi2"]
        )
        _spectrum1, _spectrum2 = _prepare_mirror_spectra(
            spectrum1, spectrum2, **drawing_controls
        )
        score, peak_matches = similarity.cosine(
            _spectrum1,
            _spectrum2,
            drawing_controls["fragment_mz_tolerance"],
            drawing_controls["cosine"] == "shifted",
        )
        peaks1 = list(zip(spectrum1.mz, spectrum1.intensity))
        peaks1 = [[float(peak[0]), float(peak[1])] for peak in peaks1]
        spectrum1_dict = {
            "peaks": peaks1,
            "n_peaks": len(spectrum1.mz),
            "precursor_mz": spectrum1.precursor_mz,
            "splash": splash_key1,
        }
        peaks2 = list(zip(spectrum2.mz, spectrum2.intensity))
        peaks2 = [[float(peak[0]), float(peak[1])] for peak in peaks2]
        spectrum2_dict = {
            "peaks": peaks2,
            "n_peaks": len(spectrum2.mz),
            "precursor_mz": spectrum2.precursor_mz,
            "splash": splash_key2,
        }
        result_dict = {
            "spectrum1": spectrum1_dict,
            "spectrum2": spectrum2_dict,
            "cosine": score,
            "n_peak_matches": len(peak_matches),
            "peak_matches": peak_matches,
        }
        status = 200
    except UsiError as e:
        result_dict = {"error": {"code": e.error_code, "message": str(e)}}
        status = e.error_code
    except ValueError as e:
        result_dict = {"error": {"code": 404, "message": str(e)}}
        status = 404
    return flask.jsonify(result_dict), status


@blueprint.route("/proxi/v0.1/spectra")
def peak_proxi_json():
    try:
        usi = flask.request.args.get("usi1")
        spectrum, _, splash_key = tasks.parse_usi(usi)
        result_dict = {
            "usi": usi,
            "status": "READABLE",
            "mzs": spectrum.mz.tolist(),
            "intensities": spectrum.intensity.tolist(),
            "attributes": [
                {
                    "accession": "MS:1000744",
                    "name": "selected ion m/z",
                    "value": str(spectrum.precursor_mz),
                },
                {
                    "accession": "MS:1000041",
                    "name": "charge state",
                    "value": str(spectrum.precursor_charge),
                },
            ],
        }
        if splash_key is not None:
            result_dict["attributes"].append(
                {
                    "accession": "MS:1002599",
                    "name": "splash key",
                    "value": splash_key,
                }
            )
    except UsiError as e:
        result_dict = {"error": {"code": e.error_code, "message": str(e)}}
    except ValueError as e:
        result_dict = {"error": {"code": 404, "message": str(e)}}
    return flask.jsonify([result_dict])


@blueprint.route("/csv/")
def peak_csv():
    spectrum, _, _ = tasks.parse_usi(flask.request.args.get("usi1"))
    with io.StringIO() as csv_str:
        writer = csv.writer(csv_str)
        writer.writerow(["mz", "intensity"])
        for mz, intensity in zip(spectrum.mz, spectrum.intensity):
            writer.writerow([mz, intensity])
        csv_bytes = io.BytesIO()
        csv_bytes.write(csv_str.getvalue().encode("utf-8"))
        csv_bytes.seek(0)
        return flask.send_file(
            csv_bytes,
            mimetype="text/csv",
            as_attachment=True,
            attachment_filename=f"{spectrum.identifier}.csv",
        )


@blueprint.route("/qrcode/")
def generate_qr():
    url = flask.request.url.replace("/qrcode/", "/dashinterface/")
    qr_image = qrcode.make(url, box_size=2)
    qr_bytes = io.BytesIO()
    qr_image.save(qr_bytes, format="png")
    qr_bytes.seek(0)
    return flask.send_file(qr_bytes, "image/png")


@blueprint.errorhandler(Exception)
def render_error(error):
    if type(error) == UsiError:
        error_code = error.error_code
    else:
        error_code = 500
    if hasattr(error, "message"):
        error_message = error.message
    else:
        error_message = f"RunTime Server Error: {error}"

    return (
        flask.render_template("error.html", error=error_message),
        error_code,
    )
