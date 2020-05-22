import requests
import grequests
import os
from tqdm import tqdm
from usi_test_cases import test_usi_list
PRODUCTION_URL = os.environ.get("SERVER_URL", "https://metabolomics-usi.ucsd.edu")

def test_img():
    from urllib.parse import quote

    all_urls = []
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/svg/?usi={quote(usi)}"
        all_urls.append(url)
        url = f"{PRODUCTION_URL}/png/?usi={quote(usi)}"
        all_urls.append(url)

    all_urls = all_urls * 10

    for i in tqdm(range(1000)):
        rs = (grequests.get(u) for u in all_urls)
        grequests.map(rs)
