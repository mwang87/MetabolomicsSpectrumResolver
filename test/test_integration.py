import csv
import functools
import imghdr
import io
import itertools
import json
import sys
import unittest.mock
sys.path.insert(0, '..')

import flask
import flex
import PIL
import pytest
import requests
import spectrum_utils.spectrum as sus
import urllib.parse
from lxml import etree
from pyzbar import pyzbar

import app
import parsing
from error import UsiError

from usi_test_data import usis_to_test


@functools.lru_cache(None)
def _get_splash_remote(spectrum):
    payload = {'ions': [{'mass': float(mz), 'intensity': float(intensity)}
                        for mz, intensity in zip(spectrum.mz,
                                                 spectrum.intensity)],
               'type': 'MS'}
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    splash_response = requests.post(
        'https://splash.fiehnlab.ucdavis.edu/splash/it',
        data=json.dumps(payload), headers=headers)
    if splash_response.status_code != 200:
        pytest.skip('external SPLASH unavailable')
    return splash_response.text


def _get_custom_plotting_args_str():
    width, height = 20.0, 10.0
    mz_min, mz_max = 50.0, 500.0
    max_intensity = 175.0
    grid = 'true'
    annotate_precision = 2
    annotation_rotation = 45
    cosine = 'shifted'
    fragment_mz_tolerance = 0.5
    return (f'&width={width}&height={height}'
            f'&mz_min={mz_min}&mz_max={mz_max}'
            f'&max_intensity={max_intensity}'
            f'&grid={grid}'
            f'&annotate_precision={annotate_precision}'
            f'&annotation_rotation={annotation_rotation}'
            f'&cosine={cosine}'
            f'&fragment_mz_tolerance={fragment_mz_tolerance}')


@pytest.fixture(autouse=True)
def clear_cache():
    parsing.parse_usi.cache_clear()


@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


def test_render_homepage(client):
    response = client.get('/')
    assert response.status_code == 200


def test_render_contributors(client):
    response = client.get('/contributors')
    assert response.status_code == 200


def test_render_heartbeat(client):
    response = client.get('/heartbeat')
    assert response.status_code == 200
    assert json.loads(response.data) == {'status': 'success'}


def test_render_spectrum(client):
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        assert usi.encode() in response.data


def test_render_spectrum_drawing_controls_width_height(client):
    parser = etree.HTMLParser()
    width, height = 20.0, 10.0
    plotting_args = f'width={width}&height={height}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert float(html.xpath('//input[@id="width"]/@value')[0]) == width
        assert float(html.xpath('//input[@id="height"]/@value')[0]) == height


def test_render_spectrum_drawing_controls_mz_min_mz_max(client):
    parser = etree.HTMLParser()
    mz_min, mz_max = 50.0, 500.0
    plotting_args = f'mz_min={mz_min}&mz_max={mz_max}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert float(html.xpath('//input[@id="mz_min"]/@value')[0]) == mz_min
        assert float(html.xpath('//input[@id="mz_max"]/@value')[0]) == mz_max


def test_render_spectrum_drawing_controls_max_intensity(client):
    parser = etree.HTMLParser()
    max_intensity = 150.0
    plotting_args = f'max_intensity={max_intensity}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert (float(html.xpath('//input[@id="max_intensity"]/@value')[0])
                == max_intensity)


def test_render_spectrum_drawing_controls_grid_on(client):
    parser = etree.HTMLParser()
    grid = 'true'
    plotting_args = f'grid={grid}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert html.xpath('//input[@id="grid"]/@checked')[0] == 'checked'


def test_render_spectrum_drawing_controls_grid_off(client):
    parser = etree.HTMLParser()
    grid = 'false'
    plotting_args = f'grid={grid}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert len(html.xpath('//input[@id="grid"]/@checked')) == 0


def test_render_spectrum_drawing_controls_annotate_peaks(client):
    usi = 'mzspec:MS2LDA:TASK-190:accession:270684'
    for annotate_peaks in ['[[]]', '[[75.0225,93.0575,128.0275,139.0075]]']:
        plotting_args = f'annotate_peaks={annotate_peaks}'
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200


def test_render_spectrum_drawing_controls_annotate_precision(client):
    parser = etree.HTMLParser()
    annotate_precision = 2
    plotting_args = f'annotate_precision={annotate_precision}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert (int(html.xpath('//input[@id="annotate_precision"]/@value')[0])
                == annotate_precision)


def test_render_spectrum_drawing_controls_annotation_rotation(client):
    parser = etree.HTMLParser()
    annotation_rotation = 45
    plotting_args = f'annotation_rotation={annotation_rotation}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert (float(html.xpath('//input[@id="annotation_rotation"]'
                                 '/@value')[0])
                == annotation_rotation)


def test_render_spectrum_drawing_controls_cosine(client):
    parser = etree.HTMLParser()
    for cosine in ['off', 'standard', 'shifted']:
        plotting_args = f'cosine={cosine}'
        for usi in usis_to_test:
            response = client.get(
                '/spectrum/',
                query_string=f'usi={urllib.parse.quote_plus(usi)}'
                             f'&{plotting_args}')
            assert response.status_code == 200
            # Test whether the plotting arguments are reflected in the drawing
            # controls.
            html = etree.parse(io.BytesIO(response.data), parser)
            assert (html.xpath(f'//select[@id="cosine"]'
                               f'/option[@value="{cosine}"]/@selected')[0]
                    == 'selected')
            assert (len(html.xpath(f'//select[@id="cosine"]'
                                   f'/option[@value!="{cosine}"]/@selected'))
                    == 0)


def test_render_spectrum_drawing_controls_fragment_mz_tolerance(client):
    parser = etree.HTMLParser()
    fragment_mz_tolerance = 0.5
    plotting_args = f'fragment_mz_tolerance={fragment_mz_tolerance}'
    for usi in usis_to_test:
        response = client.get(
            '/spectrum/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert (float(html.xpath('//input[@id="fragment_mz_tolerance"]'
                                 '/@value')[0])
                == fragment_mz_tolerance)


# itertools recipe.
def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def test_render_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/mirror/', query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                                     f'usi2={urllib.parse.quote_plus(usi2)}')
        assert response.status_code == 200
        assert usi1.encode() in response.data
        assert usi2.encode() in response.data


def test_render_mirror_drawing_controls(client):
    parser = etree.HTMLParser()
    width, height = 20.0, 10.0
    mz_min, mz_max = 50.0, 500.0
    max_intensity = 175.0
    grid = 'true'
    annotate_precision = 2
    annotation_rotation = 45
    cosine = 'shifted'
    fragment_mz_tolerance = 0.5
    plotting_args = (f'&width={width}&height={height}'
                     f'&mz_min={mz_min}&mz_max={mz_max}'
                     f'&max_intensity={max_intensity}'
                     f'&grid={grid}'
                     f'&annotate_precision={annotate_precision}'
                     f'&annotation_rotation={annotation_rotation}'
                     f'&cosine={cosine}'
                     f'&fragment_mz_tolerance={fragment_mz_tolerance}')
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/mirror/', query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                                     f'usi2={urllib.parse.quote_plus(usi2)}&'
                                     f'{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert float(html.xpath('//input[@id="width"]/@value')[0]) == width
        assert float(html.xpath('//input[@id="height"]/@value')[0]) == height
        assert float(html.xpath('//input[@id="mz_min"]/@value')[0]) == mz_min
        assert float(html.xpath('//input[@id="mz_max"]/@value')[0]) == mz_max
        assert (float(html.xpath('//input[@id="max_intensity"]/@value')[0])
                == max_intensity)
        assert html.xpath('//input[@id="grid"]/@checked')[0] == 'checked'
        assert (int(html.xpath('//input[@id="annotate_precision"]/@value')[0])
                == annotate_precision)
        assert (float(html.xpath('//input[@id="annotation_rotation"]'
                                 '/@value')[0])
                == annotation_rotation)
        assert (html.xpath(f'//select[@id="cosine"]'
                           f'/option[@value="{cosine}"]/@selected')[0]
                == 'selected')
        assert (len(html.xpath(f'//select[@id="cosine"]'
                               f'/option[@value!="{cosine}"]/@selected'))
                == 0)
        assert (float(html.xpath('//input[@id="fragment_mz_tolerance"]'
                                 '/@value')[0])
                == fragment_mz_tolerance)


def test_generate_png(client):
    for usi in usis_to_test:
        response = client.get(
            '/png/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            '/png/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/png/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/png/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}&'
                         f'{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_svg(client):
    for usi in usis_to_test:
        response = client.get(
            '/svg/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            '/svg/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/svg/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/svg/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}&'
                         f'{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_peak_json(client):
    for usi in usis_to_test:
        response = client.get(
            '/json/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert 'peaks' in response_dict
        assert 'n_peaks' in response_dict
        assert 'precursor_mz' in response_dict
        assert 'splash' in response_dict
        assert response_dict['n_peaks'] == len(response_dict['peaks'])
        for peak in response_dict['peaks']:
            assert len(peak) == 2
        mz, intensity = zip(*response_dict['peaks'])
        assert response_dict['splash'] == _get_splash_remote(
            sus.MsmsSpectrum(usi, 0, 0, mz, intensity))


def test_peak_json_invalid(client):
    for usi, status_code in zip(*_get_invalid_usi_status_code()):
        if usi is not None:
            response = client.get(
                '/json/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
            assert response.status_code == 200
            response_dict = json.loads(response.data)
            assert 'error' in response_dict
            assert response_dict['error']['code'] == status_code, usi
            assert 'message' in response_dict['error']


def test_peak_proxi_json(client):
    schema = flex.core.load('https://raw.githubusercontent.com/HUPO-PSI/'
                            'proxi-schemas/master/specs/swagger.yaml')
    for usi in usis_to_test:
        response = client.get(
            '/proxi/v0.1/spectra',
            query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)[0]
        assert 'usi' in response_dict
        assert 'status' in response_dict
        assert response_dict['status'] == 'READABLE'
        assert 'mzs' in response_dict
        assert 'intensities' in response_dict
        assert len(response_dict['mzs']) == len(response_dict['intensities'])
        assert 'attributes' in response_dict
        for attribute in response_dict['attributes']:
            assert 'accession' in attribute
            assert 'name' in attribute
            assert 'value' in attribute
            if attribute['accession'] == 'MS:1000744':
                assert attribute['name'] == 'selected ion m/z'
            elif attribute['accession'] == 'MS:1000041':
                assert attribute['name'] == 'charge state'
            elif attribute['accession'] == 'MS:1002599':
                assert attribute['name'] == 'splash key'
                assert attribute['value'] == _get_splash_remote(
                    sus.MsmsSpectrum(usi, 0, 0, response_dict['mzs'],
                                     response_dict['intensities']))

        # Validate that the response matches the PROXI Swagger API definition.
        flex.core.validate_api_response(schema, raw_request=flask.request,
                                        raw_response=response)


def test_peak_proxi_json_invalid(client):
    for usi, status_code in zip(*_get_invalid_usi_status_code()):
        if usi is not None:
            response = client.get(
                '/proxi/v0.1/spectra',
                query_string=f'usi={urllib.parse.quote_plus(usi)}')
            assert response.status_code == 200
            response_dict = json.loads(response.data)[0]
            assert 'error' in response_dict
            assert response_dict['error']['code'] == status_code, usi
            assert 'message' in response_dict['error']


def test_peak_csv(client):
    for usi in usis_to_test:
        response = client.get(
            '/csv/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        with io.StringIO(response.data.decode()) as response_csv:
            csv_reader = csv.reader(response_csv)
            assert next(csv_reader) == ['mz', 'intensity']
            for peak in csv_reader:
                assert len(peak) == 2


def test_peak_csv_invalid(client):
    for usi, status_code in zip(*_get_invalid_usi_status_code()):
        if usi is not None:
            response = client.get(
                '/csv/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
            assert response.status_code == status_code, usi


def test_mirror_json(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/json/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert 'spectrum1' in response_dict
        assert 'spectrum2' in response_dict
        assert 'cosine' in response_dict
        assert 'n_peak_matches' in response_dict
        assert 'peak_matches' in response_dict
        assert (response_dict['n_peak_matches']
                == len(response_dict['peak_matches']))
        for peak_match in response_dict['peak_matches']:
            assert len(peak_match) == 2
        for i, usi in enumerate((usi1, usi2), 1):
            mz, intensity = zip(*response_dict[f'spectrum{i}']['peaks'])
            assert (response_dict[f'spectrum{i}']['splash']
                    == _get_splash_remote(sus.MsmsSpectrum(usi, 0, 0, mz,
                                                           intensity)))


def test_generate_qr(client):
    for usi in usis_to_test:
        response = client.get(
            '/qrcode/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f'/spectrum/?usi={urllib.parse.quote_plus(usi)}')


def test_generate_qr_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi in usis_to_test:
        response = client.get(
            '/qrcode/',
            query_string=f'usi={urllib.parse.quote_plus(usi)}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f'/spectrum/?usi={urllib.parse.quote_plus(usi)}&'
                    f'{plotting_args}')


def test_generate_qr_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/qrcode/',
            query_string=f'mirror=true&usi1={urllib.parse.quote_plus(usi1)}&'
                         f'usi2={urllib.parse.quote_plus(usi2)}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f'/mirror/?usi1={urllib.parse.quote_plus(usi1)}&'
                    f'usi2={urllib.parse.quote_plus(usi2)}')


def test_generate_qr_mirror_drawing_controls(client):
    plotting_args = _get_custom_plotting_args_str()
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get(
            '/qrcode/',
            query_string=f'mirror=true&usi1={urllib.parse.quote_plus(usi1)}'
                         f'&usi2={urllib.parse.quote_plus(usi2)}&'
                         f'{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'
        with io.BytesIO(response.data) as image_bytes:
            with PIL.Image.open(image_bytes) as image:
                qr = pyzbar.decode(image)[0]
                assert urllib.parse.unquote(qr.data.decode()).endswith(
                    f'/mirror/?usi1={urllib.parse.quote_plus(usi1)}&'
                    f'usi2={urllib.parse.quote_plus(usi2)}&{plotting_args}')


def test_render_error(client):
    for usi, status_code in zip(*_get_invalid_usi_status_code()):
        if usi is not None:
            response = client.get(
                '/spectrum/',
                query_string=f'usi={urllib.parse.quote_plus(usi)}')
            assert response.status_code == status_code, usi


def test_render_error_timeout(client):
    with unittest.mock.patch(
            'parsing.requests.get',
            side_effect=UsiError('Timeout while retrieving the USI from an '
                                 'external resource', 504)) as _:
        usi = 'mzspec:MASSBANK::accession:SM858102'
        response = client.get(
            '/spectrum/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504
        response = client.get(
            '/png/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504
        response = client.get(
            '/svg/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504
        response = client.get(
            '/mirror/', query_string=f'usi1={urllib.parse.quote_plus(usi)}&'
                                     f'usi2={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504
        response = client.get(
            '/png/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi)}&'
                         f'usi2={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504
        response = client.get(
            '/svg/mirror/',
            query_string=f'usi1={urllib.parse.quote_plus(usi)}&'
                         f'usi2={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504

        response = client.get(
            '/json/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert 'error' in response_dict
        assert response_dict['error']['code'] == 504
        assert 'message' in response_dict['error']

        response = client.get(
            '/proxi/v0.1/spectra',
            query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)[0]
        assert 'error' in response_dict
        assert response_dict['error']['code'] == 504
        assert 'message' in response_dict['error']

        response = client.get(
            '/csv/', query_string=f'usi={urllib.parse.quote_plus(usi)}')
        assert response.status_code == 504


def _get_invalid_usi_status_code():
    usis = [
        # Invalid USI.
        'this:is:not:a:valid:usi',
        # Invalid preamble.
        None,
        # 'not_mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:
        #  scan:17555',
        # Invalid collection.
        'mzspec:PXD000000000:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555',
        'mzspec:RANDOM666:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555',
        # Invalid index.
        None,
        # 'mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:
        #  not_scan:17555',
        # Missing index.
        'mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:',
        'mzspec:GNPS:TASK-666c95481f0c53d42e78a61bf899e9f9adb-spectra/'
        'specs_ms.mgf:scan:1943',
        'mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/'
        'specs_ms.mgf:index:1943',
        'mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/'
        'nonexisting.mgf:scan:1943',
        'mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/'
        'specs_ms.mgf:scan:this_scan_does_not_exist',
        'mzspec:GNPS:GNPS-LIBRARY:index:CCMSLIB00005436077',
        'mzspec:GNPS:GNPS-LIBRARY:accession:this_accession_does_not_exist',
        'mzspec:MASSBANK::index:SM858102',
        'mzspec:MASSBANK::accession:this_accession_does_not_exist',
        'mzspec:MS2LDA:TASK-bla190:accession:270684',
        'mzspec:MS2LDA:TASK-190:index:270684',
        'mzspec:MS2LDA:TASK-666666666:accession:270684',
        'mzspec:MS2LDA:TASK-190:accession:this_document_does_not_exist',
        'mzspec:MSV666666666:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555',
        'mzspec:MSV000079514:this_filename_does_not_exist:scan:17555',
        'mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:index:17555',
        'mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:'
        'this_scan_does_not_exist',
        'mzspec:MOTIFDB::index:171163',
        'mzspec:MOTIFDB::accession:this_index_does_not_exist'
    ]
    status_codes = [400, 400, 400, 400, 400, 400, 400, 400, 404, 404, 400, 404,
                    400, 404, 400, 400, 404, 404, 404, 404, 400, 404, 400, 404]
    return usis, status_codes
