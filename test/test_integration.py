import imghdr
import io
import itertools
import json
import sys
sys.path.insert(0, '..')

import pytest
from lxml import etree

import app

from usi_test_data import usis_to_test


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
        response = client.get('/spectrum/', query_string=f'usi={usi}')
        assert response.status_code == 200
        assert usi.encode() in response.data


def test_render_spectrum_drawing_controls_width_height(client):
    parser = etree.HTMLParser()
    width, height = 20.0, 10.0
    plotting_args = f'width={width}&height={height}'
    for usi in usis_to_test:
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
        assert response.status_code == 200
        # Test whether the plotting arguments are reflected in the drawing
        # controls.
        html = etree.parse(io.BytesIO(response.data), parser)
        assert len(html.xpath('//input[@id="grid"]/@checked')) == 0


def test_render_spectrum_drawing_controls_annotate_peaks(client):
    usi = 'mzspec:MS2LDA:TASK-190:accession:270684'
    for annotate_peaks in ['[[]]', '[[75.0225,93.0575,128.0275,139.0075]]']:
        plotting_args = f'annotate_peaks={annotate_peaks}'
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
        assert response.status_code == 200


def test_render_spectrum_drawing_controls_annotate_precision(client):
    parser = etree.HTMLParser()
    annotate_precision = 2
    plotting_args = f'annotate_precision={annotate_precision}'
    for usi in usis_to_test:
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
            response = client.get('/spectrum/',
                                  query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/spectrum/',
                              query_string=f'usi={usi}&{plotting_args}')
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
        response = client.get('/mirror/',
                              query_string=f'usi1={usi1}&usi2={usi2}')
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
            '/mirror/',
            query_string=f'usi1={usi1}&usi2={usi2}&{plotting_args}')
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
        response = client.get('/png/', query_string=f'usi={usi}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_drawing_controls(client):
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
    for usi in usis_to_test:
        response = client.get('/png/',
                              query_string=f'usi={usi}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get('/png/mirror/',
                              query_string=f'usi1={usi1}&usi2={usi2}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_png_mirror_drawing_controls(client):
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
            '/png/mirror/',
            query_string=f'usi1={usi1}&usi2={usi2}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert imghdr.what(None, response.data) == 'png'


def test_generate_svg(client):
    for usi in usis_to_test:
        response = client.get('/svg/', query_string=f'usi={usi}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_drawing_controls(client):
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
    for usi in usis_to_test:
        response = client.get('/svg/',
                              query_string=f'usi={usi}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_mirror(client):
    for usi1, usi2 in pairwise(usis_to_test):
        response = client.get('/svg/mirror/',
                              query_string=f'usi1={usi1}&usi2={usi2}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_generate_svg_mirror_drawing_controls(client):
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
            '/svg/mirror/',
            query_string=f'usi1={usi1}&usi2={usi2}&{plotting_args}')
        assert response.status_code == 200
        assert len(response.data) > 0
        assert b'<!DOCTYPE svg' in response.data


def test_peak_json(client):
    for usi in usis_to_test:
        response = client.get('/json/', query_string=f'usi={usi}')
        assert response.status_code == 200
        response_dict = json.loads(response.data)
        assert 'peaks' in response_dict
        assert 'n_peaks' in response_dict
        assert 'precursor_mz' in response_dict
        assert response_dict['n_peaks'] == len(response_dict['peaks'])
        for peak in response_dict['peaks']:
            assert len(peak) == 2


def test_peak_json_invalid(client):
    usi = 'this:is:not:a:valid:usi'
    response = client.get('/json/', query_string=f'usi={usi}')
    assert response.status_code == 200
    response_dict = json.loads(response.data)
    assert 'error' in response_dict
    assert response_dict['error']['code'] == 404
    assert 'message' in response_dict['error']


def test_peak_proxi_json(client):
    for usi in usis_to_test:
        response = client.get('/api/proxi/v0.1/spectra',
                              query_string=f'usi={usi}')
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
        # TODO: Validate using the PROXI swagger definition.
        #   https://github.com/HUPO-PSI/proxi-schemas/blob/master/specs/swagger.yaml


def test_peak_proxi_json_invalid(client):
    usi = 'this:is:not:a:valid:usi'
    response = client.get('/api/proxi/v0.1/spectra', query_string=f'usi={usi}')
    assert response.status_code == 200
    response_dict = json.loads(response.data)
    assert 'error' in response_dict
    assert response_dict['error']['code'] == 404
    assert 'message' in response_dict['error']


def test_internal_error(client):
    usi = 'this:is:not:a:valid:usi'
    response = client.get('/spectrum/', query_string=f'usi={usi}')
    assert response.status_code == 500
