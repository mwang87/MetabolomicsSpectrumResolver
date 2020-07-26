import itertools
import os

import grequests
from tqdm import tqdm
from urllib.parse import quote

from metabolomics_spectrum_resolver.usi_test_cases import test_usi_list


PRODUCTION_URL = os.environ.get(
    'SERVER_URL', 'https://metabolomics-usi.ucsd.edu')


def test_img():
    all_urls = []
    for usi in test_usi_list:
        all_urls.append(f'{PRODUCTION_URL}/svg/?usi={quote(usi)}')
        all_urls.append(f'{PRODUCTION_URL}/png/?usi={quote(usi)}')

    for _ in tqdm(range(1000)):
        grequests.map(grequests.get(u) for u in itertools.chain.from_iterable(
            itertools.repeat(all_urls, 10)))
