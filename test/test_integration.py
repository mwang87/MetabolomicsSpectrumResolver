import csv
import functools
import imghdr
import io
import itertools
import json
import unittest.mock

import flask
import flex
import PIL
import pytest
import requests
import spectrum_utils.spectrum as sus
import urllib.parse
from pyzbar import pyzbar

from metabolomics_spectrum_resolver import app
from metabolomics_spectrum_resolver.error import UsiError

from usi_test_data import usis_to_test
from peak_test_data import peaks_to_test


@functools.lru_cache(None)
def _get_splash_remote(spectrum):
    payload = {
        "ions": [
            {"mass": float(mz), "intensity": float(intensity)}
            for mz, intensity in zip(spectrum.mz, spectrum.intensity)
        ],
        "type": "MS",
    }
    headers = {"Content-type": "application/json; charset=UTF-8"}
    splash_response = requests.post(
        "https://splash.fiehnlab.ucdavis.edu/splash/it",
        data=json.dumps(payload),
        headers=headers,
        verify=False
    )
    if splash_response.status_code != 200:
        pytest.skip("external SPLASH unavailable")
    return splash_response.text


def _get_custom_plotting_args_str():
    width, height = 20.0, 10.0
    mz_min, mz_max = 50.0, 500.0
    max_intensity = 175.0
    grid = "true"
    annotate_precision = 2
    annotation_rotation = 45
    cosine = "shifted"
    fragment_mz_tolerance = 0.5
    return (
        f"&width={width}&height={height}"
        f"&mz_min={mz_min}&mz_max={mz_max}"
        f"&max_intensity={max_intensity}"
        f"&grid={grid}"
        f"&annotate_precision={annotate_precision}"
        f"&annotation_rotation={annotation_rotation}"
        f"&cosine={cosine}"
        f"&fragment_mz_tolerance={fragment_mz_tolerance}"
    )


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client


def test_render_homepage(client):
    response = client.get("/")
    assert response.status_code == 200


def test_render_contributors(client):
    response = client.get("/contributors")
    assert response.status_code == 200


def test_render_heartbeat(client):
    response = client.get("/heartbeat")
    assert response.status_code == 200
    assert json.loads(response.data) == {"status": "success"}


def test_render_spectrum(client):
    for usi in usis_to_test:
        response = client.get(
            "/spectrum/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 302


# itertools recipe.
def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def test_render_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}",
        )
        assert response.status_code == 302


def test_generate_png(client):
    for usi in usis_to_test:
        response = client.get(
            "/png/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"


def test_generate_png_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            "/png/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"


def test_generate_png_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/png/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"


def test_generate_png_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/png/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"


def test_generate_svg(client):
    for usi in usis_to_test:
        response = client.get(
            "/svg/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data

def test_generate_svg_peaks(client):
    for spectrum1 in peaks_to_test:
        response = client.post(
            "/svg/",
            query_string="usi1=",
            json={
                "spectrum1": spectrum1,
            }
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data

def test_generate_svg_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            "/svg/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data


def test_generate_svg_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/svg/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data


def test_generate_svg_mirror_peaks(client):
    for spectrum1, spectrum2 in pairwise(peaks_to_test):
        response = client.post(
            "/svg/mirror/",
            query_string="usi1=&usi2=",
            json={
                "spectrum1": spectrum1,
                "spectrum2": spectrum2,
            }
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data


def test_generate_svg_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/svg/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b"<!DOCTYPE svg" in response.data


def test_peak_json(client):
    for usi in usis_to_test:
        response = client.get(
            "/json/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert "peaks" in response_dict
        assert "n_peaks" in response_dict
        assert "precursor_mz" in response_dict
        assert "splash" in response_dict
        assert response_dict["n_peaks"] == len(response_dict["peaks"])
        for peak in response_dict["peaks"]:
            assert len(peak) == 2
        mz, intensity = zip(*response_dict["peaks"])
        assert response_dict["splash"] == _get_splash_remote(
            sus.MsmsSpectrum(usi, 0, 0, mz, intensity)
        )


def test_peak_json_invalid(client):
    for usi, status_code in _get_invalid_usi_status_code():
        if usi is not None:
            response = client.get(
                "/json/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
            )
            assert response.status_code == status_code
            response_dict = json.loads(response.data)
            assert "error" in response_dict
            assert response_dict["error"]["code"] == status_code, usi
            assert "message" in response_dict["error"]


def test_peak_proxi_json(client):
    schema = flex.core.load(
        "https://raw.githubusercontent.com/HUPO-PSI/"
        "proxi-schemas/master/specs/swagger.yaml"
    )
    for usi in usis_to_test:
        response = client.get(
            "/proxi/v0.1/spectra",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}",
        )
        assert response.status_code == 200
        response_dict = json.loads(response.data)[0]
        assert "usi" in response_dict
        assert "status" in response_dict
        assert response_dict["status"] == "READABLE"
        assert "mzs" in response_dict
        assert "intensities" in response_dict
        assert len(response_dict["mzs"]) == len(response_dict["intensities"])
        assert "attributes" in response_dict
        for attribute in response_dict["attributes"]:
            assert "accession" in attribute
            assert "name" in attribute
            assert "value" in attribute
            if attribute["accession"] == "MS:1000744":
                assert attribute["name"] == "selected ion m/z"
            elif attribute["accession"] == "MS:1000041":
                assert attribute["name"] == "charge state"
            elif attribute["accession"] == "MS:1002599":
                assert attribute["name"] == "splash key"
                assert attribute["value"] == _get_splash_remote(
                    sus.MsmsSpectrum(
                        usi,
                        0,
                        0,
                        response_dict["mzs"],
                        response_dict["intensities"],
                    )
                )

        # Validate that the response matches the PROXI Swagger API definition.
        flex.core.validate_api_response(
            schema, raw_request=flask.request, raw_response=response
        )


def test_peak_proxi_json_invalid(client):
    for usi, status_code in _get_invalid_usi_status_code():
        if usi is not None:
            response = client.get(
                "/proxi/v0.1/spectra",
                query_string=f"usi1={urllib.parse.quote_plus(usi)}",
            )
            assert response.status_code == 200
            response_dict = json.loads(response.data)[0]
            assert "error" in response_dict
            assert response_dict["error"]["code"] == status_code, usi
            assert "message" in response_dict["error"]


def test_peak_csv(client):
    for usi in usis_to_test:
        response = client.get(
            "/csv/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        with io.StringIO(response.data.decode()) as response_csv:
            csv_reader = csv.reader(response_csv)
            assert next(csv_reader) == ["mz", "intensity"]
            for peak in csv_reader:
                assert len(peak) == 2


def test_peak_csv_invalid(client):
    for usi, status_code in _get_invalid_usi_status_code():
        if usi is not None:
            response = client.get(
                "/csv/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
            )
            assert response.status_code == status_code, usi


def test_mirror_json(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/json/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}",
        )
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert "spectrum1" in response_dict
        assert "spectrum2" in response_dict
        assert "cosine" in response_dict
        assert "n_peak_matches" in response_dict
        assert "peak_matches" in response_dict
        assert response_dict["n_peak_matches"] == len(
            response_dict["peak_matches"]
        )
        for peak_match in response_dict["peak_matches"]:
            assert len(peak_match) == 2
        for i, usi in enumerate((usi1, usi2), 1):
            mz, intensity = zip(*response_dict[f"spectrum{i}"]["peaks"])
            assert response_dict[f"spectrum{i}"][
                "splash"
            ] == _get_splash_remote(sus.MsmsSpectrum(usi, 0, 0, mz, intensity))


def test_generate_qr(client):
    for usi in usis_to_test:
        response = client.get(
            "/qrcode/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f"/dashinterface/?usi1={usi}"
                )


def test_generate_qr_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            "/qrcode/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f"/dashinterface/?usi1={usi}&{plotting_args}"
                )


def test_generate_qr_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/qrcode/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}&"
            f"usi2={urllib.parse.quote_plus(usi2)}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f"/dashinterface/?usi1={usi1}&usi2={usi2}"
                )


def test_generate_qr_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            "/qrcode/",
            query_string=f"usi1={urllib.parse.quote_plus(usi1)}"
            f"&usi2={urllib.parse.quote_plus(usi2)}&"
            f"{plotting_args}",
        )
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == "png"
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f"/dashinterface/?usi1={usi1}&usi2={usi2}&{plotting_args}"
                )


def test_render_error(client):
    for usi, status_code in _get_invalid_usi_status_code():
        if usi is not None:
            response = client.get(
                "/json/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
            )

            assert response.status_code == status_code, usi


# FIXME
@pytest.mark.skip(reason="Mock seems to have some issues")
def test_render_error_timeout(client):
    with unittest.mock.patch(
        "metabolomics_spectrum_resolver.parsing.requests.get",
        side_effect=UsiError(
            "Timeout while retrieving the USI from an " "external resource",
            504,
        ),
    ) as _:
        usi = "mzspec:MASSBANK::accession:SM858102"
        response = client.get(
            "/png/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 504
        response = client.get(
            "/svg/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 504
        response = client.get(
            "/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"usi2={urllib.parse.quote_plus(usi)}",
        )
        assert response.status_code == 504
        response = client.get(
            "/png/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"usi2={urllib.parse.quote_plus(usi)}",
        )
        assert response.status_code == 504
        response = client.get(
            "/svg/mirror/",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}&"
            f"usi2={urllib.parse.quote_plus(usi)}",
        )
        assert response.status_code == 504

        response = client.get(
            "/json/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert "error" in response_dict
        assert response_dict["error"]["code"] == 504
        assert "message" in response_dict["error"]

        response = client.get(
            "/proxi/v0.1/spectra",
            query_string=f"usi1={urllib.parse.quote_plus(usi)}",
        )
        assert response.status_code == 200
        response_dict = json.loads(response.data)[0]
        assert "error" in response_dict
        assert response_dict["error"]["code"] == 504
        assert "message" in response_dict["error"]

        response = client.get(
            "/csv/", query_string=f"usi1={urllib.parse.quote_plus(usi)}"
        )
        assert response.status_code == 504


def _get_invalid_usi_status_code():
    return [
        # Invalid USI.
        ("this:is:not:a:valid:usi", 400),
        # Invalid preamble.
        # FIXME
        # not_mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555
        (None, 400),
        # Invalid collection.
        (
            "mzspec:PXD000000000:Adult_Frontalcortex_bRP_Elite_85_f09:scan:"
            "17555",
            400,
        ),
        (
            "mzspec:RANDOM666:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555",
            400,
        ),
        # Invalid index.
        # FIXME
        # mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:not_scan:17555
        (None, 400),
        # Missing index.
        ("mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:", 400),
        (
            "mzspec:GNPS:TASK-666c95481f0c53d42e78a61bf899e9f9adb-spectra/"
            "specs_ms.mgf:scan:1943",
            400,
        ),
        (
            "mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/"
            "specs_ms.mgf:index:1943",
            400,
        ),
        (
            "mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/"
            "nonexisting.mgf:scan:1943",
            404,
        ),
        (
            "mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/"
            "specs_ms.mgf:scan:this_scan_does_not_exist",
            404,
        ),
        ("mzspec:GNPS:GNPS-LIBRARY:index:CCMSLIB00005436077", 400),
        (
            "mzspec:GNPS:GNPS-LIBRARY:accession:this_accession_does_not_exist",
            404,
        ),
        ("mzspec:MASSBANK::index:SM858102", 400),
        ("mzspec:MASSBANK::accession:this_accession_does_not_exist", 404),
        ("mzspec:MS2LDA:TASK-bla190:accession:270684", 400),
        ("mzspec:MS2LDA:TASK-190:index:270684", 400),
        ("mzspec:MS2LDA:TASK-666666666:accession:270684", 404),
        ("mzspec:MS2LDA:TASK-190:accession:this_document_does_not_exist", 404),
        (
            "mzspec:MSV666666666:Adult_Frontalcortex_bRP_Elite_85_f09:scan:"
            "17555",
            404,
        ),
        ("mzspec:MSV000079514:this_filename_does_not_exist:scan:17555", 404),
        (
            "mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:index:"
            "17555",
            400,
        ),
        (
            "mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:"
            "this_scan_does_not_exist",
            404,
        ),
        ("mzspec:MOTIFDB::index:171163", 400),
        ("mzspec:MOTIFDB::accession:this_index_does_not_exist", 404),
    ]
