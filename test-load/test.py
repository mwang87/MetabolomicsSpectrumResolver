import itertools
import os

import grequests
from tqdm import tqdm
from urllib.parse import quote

import usi_test_cases


PRODUCTION_URL = os.environ.get(
    'SERVER_URL', 'https://metabolomics-usi.ucsd.edu')


def test_img():
    all_urls = []
    for usi in usi_test_cases.test_usi_list:
        all_urls.append(f'{PRODUCTION_URL}/svg/?usi={quote(usi)}')
        all_urls.append(f'{PRODUCTION_URL}/png/?usi={quote(usi)}')

    for _ in tqdm(range(1000)):
        grequests.map(grequests.get(u) for u in itertools.chain.from_iterable(
            itertools.repeat(all_urls, 10)))
