import io
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


def test_internal_error(client):
    usi = 'this:is:not:a:valid:usi'
    response = client.get('/spectrum/', query_string=f'usi={usi}')
    assert response.status_code == 500
