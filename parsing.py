import functools
import json
import re

import requests
import spectrum_utils.spectrum as sus


MS2LDA_SERVER = 'http://ms2lda.org/basicviz/'
MOTIFDB_SERVER = 'http://ms2lda.org/motifdb/'
MASSBANK_SERVER = 'https://massbank.us/rest/spectra/'

# USI specification: http://www.psidev.info/usi
usi_pattern = re.compile(
    # mzspec preamble
    '^mzspec'
    # collection identifier
    # Proteomics collection identifiers: PXDnnnnnn, MSVnnnnnnnnn, RPXDnnnnnn,
    #                                    PXLnnnnnn
    # Unofficial: MASSIVEKB
    # https://github.com/HUPO-PSI/usi/blob/master/CollectionIdentifiers.md
    ':(MSV\d{9}|PXD\d{6}|PXL\d{6}|RPXD\d{6}|MASSIVEKB|'
    # Metabolomics collection identifiers: GNPS, MASSBANK, MS2LDA, MOTIFDB
    'GNPS|MASSBANK|MS2LDA|MOTIFDB)'
    # msRun identifier
    ':(.*)'
    # index flag
    ':(scan|index|nativeId|trace|accession)'
    # index number
    ':(.+)'
    # optional spectrum interpretation
    '(:.+)?$'
)
gnps_task_pattern = re.compile('^TASK-([a-z0-9]{32})-(.+)$')
ms2lda_task_pattern = re.compile('^TASK-(\d+)$')


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


# Parse MSV or PXD library.
def _parse_massive(usi):
    match = usi_pattern.match(usi)
    collection = match.group(1)
    if collection.startswith('MSV'):
        source_link = (f'https://massive.ucsd.edu/ProteoSAFe/QueryMSV?'
                       f'id={collection}')
    elif collection.startswith('PXD'):
        source_link = (f'http://proteomecentral.proteomexchange.org/cgi/'
                       f'GetDataset?ID={collection}')
    else:
        # TODO: Support PXL, RPXD, MASSIVEKB collection identifiers.
        raise ValueError('Currently supported MassIVE collection identifiers: '
                         'PXD, MSV')
    index_flag = match.group(3)
    if index_flag != 'scan':
        raise ValueError('Currently supported MassIVE index flags: scan')
    index = match.group(4)
    lookup_url = (f'https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?'
                  f'id={usi}')
    for spectrum_file in requests.get(lookup_url).json()['row_data']:
        if any(spectrum_file['file_descriptor'].lower().endswith(
                extension.lower()) for extension in ['mzML', 'mzXML', 'MGF']):
            request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                           f'DownloadResultFile?'
                           f'task=4f2ac74ea114401787a7e96e143bb4a1&'
                           f'invoke=annotatedSpectrumImageText&block=0&'
                           f'file=FILE->{spectrum_file["file_descriptor"]}&'
                           f'scan={index}&peptide=*..*&force=false&'
                           f'uploadfile=True')
            mz, intensity = _parse_gnps_peak_text(
                requests.get(request_url).text)
            return sus.MsmsSpectrum(usi, 0, 0, mz, intensity), source_link
    raise ValueError('Unsupported/unknown MassIVE USI')


# Parse GNPS tasks or library spectra.
def _parse_gnps(usi):
    match = usi_pattern.match(usi)
    ms_run = match.group(2)
    if ms_run.startswith('TASK'):
        return _parse_gnps_task(usi)
    else:
        return _parse_gnps_library(usi)


# Parse GNPS clustered spectra in Molecular Networking.
def _parse_gnps_task(usi):
    match = usi_pattern.match(usi)
    gnps_task_match = gnps_task_pattern.match(match.group(2))
    task = gnps_task_match.group(1)
    filename = gnps_task_match.group(2)
    index_flag = match.group(3)
    if index_flag != 'scan':
        raise ValueError('Currently supported GNPS TASK index flags: scan')
    index = match.group(4)
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?'
                   f'task={task}&invoke=annotatedSpectrumImageText&'
                   f'block=0&file=FILE->{filename}&scan={index}&peptide=*..*&'
                   f'force=false&_=1561457932129')
    mz, intensity = _parse_gnps_peak_text(requests.get(request_url).text)
    source_link = (f'https://gnps.ucsd.edu/ProteoSAFe/status.jsp?'
                   f'task={task}')
    return sus.MsmsSpectrum(usi, 0, 0, mz, intensity), source_link


def _parse_gnps_peak_text(text):
    mz, intensity = [], []
    for peak in text.strip().split('\n')[8:]:   # First 8 lines are header.
        mz_int = peak.split(maxsplit=2)
        mz.append(float(mz_int[0]))
        intensity.append(float(mz_int[1]))
    return mz, intensity


# Parse GNPS library.
def _parse_gnps_library(usi):
    match = usi_pattern.match(usi)
    index_flag = match.group(3)
    if index_flag != 'accession':
        raise ValueError('Currently supported GNPS library index flags: '
                         'accession')
    index = match.group(4)
    request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/SpectrumCommentServlet?'
                   f'SpectrumID={index}')
    spectrum_dict = requests.get(request_url).json()
    mz, intensity = zip(*json.loads(
        spectrum_dict['spectruminfo']['peaks_json']))
    source_link = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                   f'gnpslibraryspectrum.jsp?SpectrumID={index}')
    return (
        sus.MsmsSpectrum(
            usi, float(spectrum_dict['annotations'][0]['Precursor_MZ']),
            int(spectrum_dict['annotations'][0]['Charge']), mz, intensity),
        source_link)


# Parse MassBank entry.
def _parse_massbank(usi):
    match = usi_pattern.match(usi)
    index_flag = match.group(3)
    if index_flag != 'accession':
        raise ValueError('Currently supported MASSBANK index flags: accession')
    index = match.group(4)
    response = requests.get(f'{MASSBANK_SERVER}{index}')
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
                   f'RecordDisplay.jsp?id={index}')
    return sus.MsmsSpectrum(usi, precursor_mz, 0, mz, intensity), source_link


# Parse MS2LDA from ms2lda.org.
def _parse_ms2lda(usi):
    match = usi_pattern.match(usi)
    ms2lda_task_match = ms2lda_task_pattern.match(match.group(2))
    experiment_id = ms2lda_task_match.group(1)
    index_flag = match.group(3)
    if index_flag != 'accession':
        raise ValueError('Currently supported MS2LDA index flags: accession')
    index = match.group(4)
    request_url = (f'{MS2LDA_SERVER}get_doc/?experiment_id={experiment_id}'
                   f'&document_id={index}')
    spectrum_dict = json.loads(requests.get(request_url).text)
    mz, intensity = zip(*spectrum_dict['peaks'])
    source_link = None
    return sus.MsmsSpectrum(usi, float(spectrum_dict['precursor_mz']), 0, mz,
                            intensity), source_link


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
