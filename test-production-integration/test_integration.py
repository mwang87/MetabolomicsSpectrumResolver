import requests
from usi_test_cases import test_usi_list
PRODUCTION_URL = "metabolomics-usi.ucsd.edu"

def test_heartbeat():
    url = f"https://{PRODUCTION_URL}/heartbeat"
    r = requests.get(url)
    r.raise_for_status()

def test_usi_pages():
    for usi in test_usi_list:
        url = f"https://{PRODUCTION_URL}/spectrum/?usi={usi}"
        r = requests.get(url)
        r.raise_for_status()
