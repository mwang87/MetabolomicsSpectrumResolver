import json

import numpy as np
import pandas as pd
import requests
import splash


def _get_splash_remote(peaks):
    payload = {'ions': [{'mass': str(peak[0]), 'intensity': str(peak[1])}
                        for peak in peaks],
               'type': 'MS'}
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    r = requests.post('https://splash.fiehnlab.ucdavis.edu/splash/it',
                      data=json.dumps(payload), headers=headers)
    return r.text


def test_splash_toy():
    peaks = [(102, 3), (100, 1), (101, 2)]
    # Local SPLASH.
    spectrum = splash.Spectrum(peaks, splash.SpectrumType.MS)
    splash_local = splash.Splash().splash(spectrum)
    # Reference remote SPLASH.
    splash_remote = _get_splash_remote(peaks)
    assert splash_local == splash_remote


def test_splash_match_api():
    # Peaks from JSON.
    r = requests.get('https://metabolomics-usi.ucsd.edu/json/?usi='
                     'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077')
    peaks = r.json()['peaks']
    splash_remote = _get_splash_remote(peaks)
    # Direct m/z values.
    spectrum = splash.Spectrum(list(map(tuple, peaks)), splash.SpectrumType.MS)
    splash_local = splash.Splash().splash(spectrum)
    assert splash_local == splash_remote
    # m/z as explicit float64/float32.
    mz, intensity = zip(*peaks)
    for dtype in [np.float64, np.float32]:
        spectrum = splash.Spectrum(list(zip(np.asarray(mz, dtype),
                                            np.asarray(intensity, dtype))),
                                   splash.SpectrumType.MS)
        splash_local = splash.Splash().splash(spectrum)
        assert splash_local == splash_remote

    # Peaks from CSV.
    df = pd.read_csv('https://metabolomics-usi.ucsd.edu/csv/?usi='
                     'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077')
    spectrum = splash.Spectrum(list(zip(df['mz'], df['intensity'])),
                               splash.SpectrumType.MS)
    splash_local = splash.Splash().splash(spectrum)
    splash_remote = _get_splash_remote(zip(df['mz'], df['intensity']))
    assert splash_local == splash_remote
