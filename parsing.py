import functools
import json

import requests
import spectrum_utils.spectrum as sus


MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'
MOTIFDB_SERVER = 'http://ms2lda.org/motifdb/'
MASSBANK_SERVER = 'https://massbank.us/rest/spectra/'


@functools.lru_cache(100)
def parse_usi(usi):
    usi_identifier = usi.lower().split(':')[1]
    if usi_identifier.startswith('gnpstask'):
        return _parse_gnps_task(usi)
    elif usi_identifier.startswith('gnpslibrary'):
        return _parse_gnps_library(usi)
    elif usi_identifier.startswith('ms2ldatask'):
        return _parse_ms2lda(usi)
    elif usi_identifier.startswith('pxd'):
        return _parse_msv_pxd(usi)
    elif usi_identifier.startswith('msv'):
        return _parse_msv_pxd(usi)
    elif usi_identifier.startswith('mtbls'):
        return _parse_mtbls(usi)
    elif usi_identifier.startswith('st'):
        return _parse_metabolomics_workbench(usi)
    elif usi_identifier.startswith('motifdb'):
        return _parse_motifdb(usi)
    elif usi_identifier.startswith('massbank'):
        return _parse_massbank(usi)
    else:
        raise ValueError(f'Unknown USI: {usi}')


# Parse GNPS clustered spectra in Molecular Networking.
def _parse_gnps_task(usi):
    tokens = usi.split(':')
    task = tokens[1].split('-')[1]
    filename = tokens[2]
    scan = tokens[4]
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?'
                   f'task={task}&invoke=annotatedSpectrumImageText&block=0&'
                   f'file=FILE->{filename}&scan={scan}&peptide=*..*&'
                   f'force=false&_=1561457932129')
    mz, intensity = _parse_gnps_peak_text(requests.get(request_url).text)
    source_link = f'https://gnps.ucsd.edu/ProteoSAFe/status.jsp?task={task}'
    return sus.MsmsSpectrum(usi, 0, 1, mz, intensity), source_link


def _parse_gnps_peak_text(text):
    mz, intensity = [], []
    for peak in text.strip().split('\n')[8:]:   # First 8 lines are header.
        mz_int = peak.split(maxsplit=2)
        mz.append(float(mz_int[0]))
        intensity.append(float(mz_int[1]))
    return mz, intensity


# Parse GNPS library.
def _parse_gnps_library(usi):
    tokens = usi.split(':')
    identifier = tokens[2]
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/SpectrumCommentServlet?'
                   f'SpectrumID={identifier}')
    spectrum_dict = requests.get(request_url).json()
    mz, intensity = zip(*json.loads(
        spectrum_dict['spectruminfo']['peaks_json']))
    source_link = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                   f'gnpslibraryspectrum.jsp?SpectrumID={identifier}')
    return sus.MsmsSpectrum(
        usi, float(spectrum_dict['annotations'][0]['Precursor_MZ']), 1, mz,
        intensity), source_link


# Parse MS2LDA from ms2lda.org.
def _parse_ms2lda(usi):
    tokens = usi.split(':')
    experiment_id = tokens[1].split('-')[1]
    document_id = tokens[3]
    request_url = (f'{MS2LDA_SERVER}get_doc/?experiment_id={experiment_id}'
                   f'&document_id={document_id}')
    spectrum_dict = json.loads(requests.get(request_url).text)
    mz, intensity = zip(*spectrum_dict['peaks'])
    source_link = None
    return sus.MsmsSpectrum(usi, float(spectrum_dict['precursor_mz']), 1, mz,
                            intensity), source_link


# Parse MSV or PXD library.
def _parse_msv_pxd(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    lookup_url = (f'https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?'
                  f'id=mzspec:{dataset_identifier}:{filename}:scan:{scan}')
    for spectrum_file in requests.get(lookup_url).json()['row_data']:
        if any(spectrum_file['file_descriptor'].lower().endswith(
                extension.lower()) for extension in ['mzML', 'mzXML', 'MGF']):
            request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                           f'DownloadResultFile?'
                           f'task=4f2ac74ea114401787a7e96e143bb4a1&'
                           f'invoke=annotatedSpectrumImageText&block=0&'
                           f'file=FILE->{spectrum_file["file_descriptor"]}&'
                           f'scan={scan}&peptide=*..*&force=false&'
                           f'uploadfile=True')
            mz, intensity = _parse_gnps_peak_text(
                requests.get(request_url).text)
            if 'PXD' in dataset_identifier:
                source_link = (f'http://proteomecentral.proteomexchange.org/'
                               f'cgi/GetDataset?ID={dataset_identifier}')
            else:
                source_link = (f'https://massive.ucsd.edu/ProteoSAFe/'
                               f'QueryMSV?id={dataset_identifier}')
            return sus.MsmsSpectrum(usi, 0, 1, mz, intensity), source_link
    raise ValueError('Unsupported/unknown USI')


def _parse_mtbls(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    for dataset in requests.get('https://massive.ucsd.edu/ProteoSAFe/'
                                'datasets_json.jsp').json()['datasets']:
        if dataset_identifier in dataset['title']:
            source_link = (f'https://www.ebi.ac.uk/'
                           f'metabolights/{dataset_identifier}')
            return _parse_msv_pxd(f'mzspec:{dataset["dataset"]}:{filename}:'
                                  f'scan:{scan}')[0], source_link
    raise ValueError('Unsupported/unknown USI')


def _parse_metabolomics_workbench(usi):
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    for dataset in requests.get('https://massive.ucsd.edu/ProteoSAFe/'
                                'datasets_json.jsp').json()['datasets']:
        if dataset_identifier in dataset['title']:
            source_link = (f'https://www.metabolomicsworkbench.org/'
                           f'data/DRCCMetadata.php?Mode=Study&StudyID=/{dataset_identifier}')
            return _parse_msv_pxd(f'mzspec:{dataset["dataset"]}:{filename}:'
                                  f'scan:{scan}')[0], source_link
    raise ValueError('Unsupported/unknown USI')

# Parse MOTIFDB from ms2lda.org.
def _parse_motifdb(usi):
    # E.g. mzspec:MOTIFDB:motif:motif_id.
    tokens = usi.split(':')
    motif_id = tokens[3]
    request_url = f'{MOTIFDB_SERVER}get_motif/{motif_id}'
    mz, intensity = zip(*json.loads(requests.get(request_url).text))
    source_link = f'http://ms2lda.org/motifdb/motif/{motif_id}/'
    return sus.MsmsSpectrum(usi, 0, 1, mz, intensity), source_link


# Parse MassBank entry.
def _parse_massbank(usi):
    # E.g. mzspec:MASSBANK:motif:motif_id.
    tokens = usi.split(':')
    massbank_id = tokens[2]
    request_url = f'{MASSBANK_SERVER}{massbank_id}'
    response = requests.get(request_url)
    spectrum_dict = response.json()
    mz, intensity = [], []
    for peak in spectrum_dict['spectrum'].split():
        peak_mz, peak_intensity = peak.split(':')
        mz.append(float(peak_mz))
        intensity.append(float(peak_intensity))
    precursor_mz = 0
    for metadata in spectrum_dict['metaData']:
        if metadata['name'] == 'precursor m/z':
            precursor_mz = float(metadata['value'])
            break
    source_link = (f'https://massbank.eu/MassBank/'
                   f'RecordDisplay.jsp?id={massbank_id}')
    return sus.MsmsSpectrum(usi, precursor_mz, 1, mz, intensity), source_link
