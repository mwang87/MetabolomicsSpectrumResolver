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

def test_error_page():
    error_usi = "mzspec:GNPSLIBRARY:CCMSLIB0000"
    url = f"{PRODUCTION_URL}/spectrum/?usi={error_usi}"

    r = requests.get(url)
    assert(r.status_code == 500)

def test_mirror_img():
    url = f"{PRODUCTION_URL}/svg/mirror?usi1=mzdata:MASSBANK:BSU00002&usi2=mzdata:MASSBANK:BSU00002"
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

def test_filtration():
    url = f"{PRODUCTION_URL}/svg/?usi=mzspec:MS2LDATASK-190:document:270684&width=10&height=6&mz_min=0&mz_max=80&max_intensity=&grid=true&annotate_peaks=[%220-4%22,%220-11%22,%220-19%22,%220-20%22]&annotate_precision=4&annotation_rotation=90"
    r = requests.get(url)
    r.raise_for_status()