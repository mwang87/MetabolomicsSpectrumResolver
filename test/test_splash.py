import splash
import requests
import pandas as pd
import json


def test_splash_toy():
    #calculating splash
    peaks = [
        (102, 3),
        (100, 1),
        (101, 2),
    ]

    splash_spectrum = splash.Spectrum(peaks, splash.SpectrumType.MS)
    splash_key = splash.Splash().splash(splash_spectrum)

    print("TOY LOCAL", splash_key)

def test_splash_toy_api():
    #calculating splash
    peaks = [
        (102, 3),
        (100, 1),
        (101, 2),
    ]

    splash_api_url = "https://splash.fiehnlab.ucdavis.edu/splash/it"
    payload = {}
    payload["ions"] = [{"mass": str(peak[0]), "intensity": str(peak[1])} for peak in peaks]
    payload["type"] = "MS"
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    r = requests.post(splash_api_url, data=json.dumps(payload), headers=headers)

    print("TOY REMOTE", r.text)


def test_splash_complex():
    r = requests.get("https://metabolomics-usi.ucsd.edu/json/?usi=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077")
    spectrum = r.json()
    peaks = spectrum["peaks"]
    peaks = [(peak[0], peak[1]) for peak in peaks]
    
    print(peaks)

    splash_spectrum = splash.Spectrum(peaks, splash.SpectrumType.MS)
    splash_key = splash.Splash().splash(splash_spectrum)

    print("COMPLEX LOCAL", splash_key)

    # Testing with Feihn API
    splash_api_url = "https://splash.fiehnlab.ucdavis.edu/splash/it"
    payload = {}
    payload["ions"] = [{"mass": str(peak[0]), "intensity": str(peak[1])} for peak in spectrum["peaks"]]
    payload["type"] = "MS"
    import json
    headers = {'Content-type': 'application/json; charset=UTF-8'}

    r = requests.post(splash_api_url, data=json.dumps(payload), headers=headers)
    print("COMPLEX REMOTE", r.text)
    

def test_splash_complex_cast_to_64():
    r = requests.get("https://metabolomics-usi.ucsd.edu/json/?usi=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077")
    spectrum = r.json()
    peaks = spectrum["peaks"]

    df = pd.DataFrame()
    df["mz"] = [peak[0] for peak in peaks]
    df["intensity"] = [peak[1] for peak in peaks]
    
    print(df.dtypes)

    splash_spectrum = splash.Spectrum(list(zip(df["mz"], df["intensity"])), splash.SpectrumType.MS)
    splash_key = splash.Splash().splash(splash_spectrum)

    print("COMPLEX CAST TO 64 LOCAL", splash_key)



def test_splash_complex2():
    df = pd.read_csv("https://metabolomics-usi.ucsd.edu/csv/?usi=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077")
    print(df.dtypes)
    print(df)

    splash_spectrum = splash.Spectrum(list(zip(df["mz"], df["intensity"])), splash.SpectrumType.MS)
    splash_key = splash.Splash().splash(splash_spectrum)

    print("COMPLEX CSV LOCAL", splash_key)


def test_splash_complex3():
    df = pd.read_csv("https://metabolomics-usi.ucsd.edu/csv/?usi=mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077")
    print(df.dtypes)
    df["mz"] = df["mz"].astype("float32")
    df["intensity"] = df["intensity"].astype("float32")

    splash_spectrum = splash.Spectrum(list(zip(df["mz"], df["intensity"])), splash.SpectrumType.MS)
    splash_key = splash.Splash().splash(splash_spectrum)

    print("COMPLEX CSV CAST to 32", splash_key)