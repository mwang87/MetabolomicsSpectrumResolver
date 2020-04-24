import requests
import os
from usi_test_cases import test_usi_list
PRODUCTION_URL = os.environ.get("SERVER_URL", "https://metabolomics-usi.ucsd.edu")

def test_heartbeat():
    url = f"{PRODUCTION_URL}/heartbeat"
    r = requests.get(url)
    r.raise_for_status()

def test_usi_pages():
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/spectrum/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()

def test_png_pages():
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/png/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()

def test_svg_pages():
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/svg/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()

def test_json():
    from urllib.parse import quote
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/json/?usi={quote(usi)}"
        r = requests.get(url)
        r.raise_for_status()

        url = f"{PRODUCTION_URL}/api/proxi/v0.1/spectra?usi={quote(usi)}"
        r = requests.get(url)
        r.raise_for_status()


def test_csv_pages():
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/csv/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()

def test_qr_pages():
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/qrcode/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()

def test_error_page():
    error_usi = "mzspec:GNPSLIBRARY:CCMSLIB0000"
    url = f"{PRODUCTION_URL}/spectrum/?usi={error_usi}"

    r = requests.get(url)
    assert(r.status_code == 500)

def test_mirror_img():
    url = f"{PRODUCTION_URL}/mirror/?usi1=mzdata:MASSBANK:BSU00002&usi2=mzdata:MASSBANK:BSU00002"
    r = requests.get(url)
    r.raise_for_status()

    url = f"{PRODUCTION_URL}/svg/mirror?usi1=mzdata:MASSBANK:BSU00002&usi2=mzdata:MASSBANK:BSU00002"
    r = requests.get(url)
    r.raise_for_status()

    url = f"{PRODUCTION_URL}/png/mirror?usi1=mzdata:MASSBANK:BSU00002&usi2=mzdata:MASSBANK:BSU00002"
    r = requests.get(url)
    r.raise_for_status()

def test_img():
    from urllib.parse import quote
    for usi in test_usi_list:
        url = f"{PRODUCTION_URL}/svg/?usi={quote(usi)}"
        r = requests.get(url)
        r.raise_for_status()

        url = f"{PRODUCTION_URL}/png/?usi={quote(usi)}"
        r = requests.get(url)
        r.raise_for_status()

