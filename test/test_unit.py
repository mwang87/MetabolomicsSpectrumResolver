import io
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


def test_render_spectrum(client):
    for usi in usis_to_test:
        response = client.get('/spectrum/', query_string=f'usi={usi}')
        assert response.status_code == 200
        assert usi.encode() in response.data
