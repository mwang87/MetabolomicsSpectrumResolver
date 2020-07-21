import functools
import json
import re

import requests
import spectrum_utils.spectrum as sus

import parsing_legacy

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
    ':(MSV\d{9}|PXD\d{6}|PXL\d{6}|RPXD\d{6})'
    # msRun identifier
    ':(.*)'
    # index flag
    ':(scan|index|nativeId|trace)'
    # index number
    ':(.+)'
    # optional spectrum interpretation
    '(:.+)?$',
    flags=re.IGNORECASE
)
# OR: Metabolomics USIs.
usi_pattern_draft = re.compile(
    # mzdraft preamble
    '^mzspec'
    # collection identifier
    # Unofficial proteomics spectral library identifier: MASSIVEKB
    # Metabolomics collection identifiers: GNPS, MASSBANK, MS2LDA, MOTIFDB
    ':(MASSIVEKB|GNPS|MASSBANK|MS2LDA|MOTIFDB)'
    # msRun identifier
    ':(.*)'
    # index flag
    ':(scan|index|nativeId|trace|accession)'
    # index number
    ':(.+)'
    # optional spectrum interpretation
    '(:.+)?$',
    flags=re.IGNORECASE
)
gnps_task_pattern = re.compile('^TASK-([a-z0-9]{32})-(.+)$',
                               flags=re.IGNORECASE)
ms2lda_task_pattern = re.compile('^TASK-(\d+)$', flags=re.IGNORECASE)


def _match_usi(usi):
    # First try matching as an official USI, then as a metabolomics draft USI.
    match = usi_pattern.match(usi)
    if match is None:
        match = usi_pattern_draft.match(usi)
    if match is None:
        raise ValueError(f'Incorrectly formatted USI: {usi}')
    return match


@functools.lru_cache(100)
def parse_usi(usi):
    try:
        match = _match_usi(usi)
    except ValueError as e:
        try:
            return parsing_legacy.parse_usi_legacy(usi)
        except ValueError:
            raise e
    collection = match.group(1).lower()
    # Send all proteomics USIs to MassIVE.
    if (collection.startswith('msv') or
            collection.startswith('pxd') or
            collection.startswith('pxl') or
            collection.startswith('rpxd') or
            collection == 'massivekb'):
        return _parse_msv_pxd(usi)
    elif collection == 'gnps':
        return _parse_gnps(usi)
    elif collection == 'massbank':
        return _parse_massbank(usi)
    elif collection == 'ms2lda':
        return _parse_ms2lda(usi)
    elif collection == 'motifdb':
        return _parse_motifdb(usi)
    else:
        raise ValueError(f'Unknown USI collection: {match.group(1)}')


# Parse GNPS tasks or library spectra.
def _parse_gnps(usi):
    match = _match_usi(usi)
    ms_run = match.group(2)
    if ms_run.lower().startswith('task'):
        return _parse_gnps_task(usi)
    else:
        return _parse_gnps_library(usi)


# Parse GNPS clustered spectra in Molecular Networking.
def _parse_gnps_task(usi):
    match = _match_usi(usi)
    gnps_task_match = gnps_task_pattern.match(match.group(2))
    if gnps_task_match is None:
        raise ValueError('Incorrectly formatted GNPS task')
    task = gnps_task_match.group(1)
    filename = gnps_task_match.group(2)
    index_flag = match.group(3)
    if index_flag.lower() != 'scan':
        raise ValueError('Currently supported GNPS TASK index flags: scan')
    scan = match.group(4)

    try:
        request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?'
                       f'task={task}&invoke=annotatedSpectrumImageText&block=0'
                       f'&file=FILE->{filename}&scan={scan}&peptide=*..*&'
                       f'force=false&_=1561457932129&format=JSON')
        lookup_request = requests.get(request_url)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        mz, intensity = zip(*spectrum_dict['peaks'])
        source_link = (f'https://gnps.ucsd.edu/ProteoSAFe/status.jsp?'
                       f'task={task}')
        if 'precursor' in spectrum_dict:
            precursor_mz = float(spectrum_dict['precursor'].get('mz', 0))
            charge = int(spectrum_dict['precursor'].get('charge', 0))
        else:
            precursor_mz, charge = 0, 0
        return (sus.MsmsSpectrum(usi, precursor_mz, charge, mz, intensity),
                source_link)
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise ValueError('Unknown GNPS task USI')


# Parse GNPS library.
def _parse_gnps_library(usi):
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != 'accession':
        raise ValueError('Currently supported GNPS library index flags: '
                         'accession')
    index = match.group(4)
    try:
        request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                       f'SpectrumCommentServlet?SpectrumID={index}')
        lookup_request = requests.get(request_url)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        if spectrum_dict['spectruminfo']['peaks_json'] == 'null':
            raise ValueError('Unknown GNPS library USI')
        mz, intensity = zip(*json.loads(
            spectrum_dict['spectruminfo']['peaks_json']))
        source_link = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                       f'gnpslibraryspectrum.jsp?SpectrumID={index}')
        return (
            sus.MsmsSpectrum(
                usi, float(spectrum_dict['annotations'][0]['Precursor_MZ']),
                int(spectrum_dict['annotations'][0]['Charge']), mz, intensity),
            source_link)
    except requests.exceptions.HTTPError:
        raise ValueError('Unknown GNPS library USI')


# Parse MassBank entry.
def _parse_massbank(usi):
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != 'accession':
        raise ValueError('Currently supported MassBank index flags: accession')
    index = match.group(4)
    try:
        lookup_request = requests.get(f'{MASSBANK_SERVER}{index}')
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
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
        return (sus.MsmsSpectrum(usi, precursor_mz, 0, mz, intensity),
                source_link)
    except requests.exceptions.HTTPError:
        raise ValueError('Unknown MassBank USI')


# Parse MS2LDA from ms2lda.org.
def _parse_ms2lda(usi):
    match = _match_usi(usi)
    ms2lda_task_match = ms2lda_task_pattern.match(match.group(2))
    if ms2lda_task_match is None:
        raise ValueError('Incorrectly formatted MS2LDA task')
    experiment_id = ms2lda_task_match.group(1)
    index_flag = match.group(3)
    if index_flag.lower() != 'accession':
        raise ValueError('Currently supported MS2LDA index flags: accession')
    index = match.group(4)
    try:
        lookup_request = requests.get(
            f'{MS2LDA_SERVER}get_doc/?experiment_id={experiment_id}'
            f'&document_id={index}')
        lookup_request.raise_for_status()
        spectrum_dict = json.loads(lookup_request.text)
        if 'error' in spectrum_dict:
            raise ValueError(f'MS2LDA error: {spectrum_dict["error"]}')
        mz, intensity = zip(*spectrum_dict['peaks'])
        source_link = None
        return sus.MsmsSpectrum(usi, float(spectrum_dict['precursor_mz']), 0,
                                mz, intensity), source_link
    except requests.exceptions.HTTPError:
        raise ValueError('Unknown MS2LDA USI')


# Parse MSV or PXD library.
def _parse_msv_pxd(usi):
    match = _match_usi(usi)
    dataset_identifier = match.group(1)
    index_flag = match.group(3)
    if index_flag.lower() != 'scan':
        raise ValueError('Currently supported MassIVE index flags: scan')
    scan = match.group(4)
    try:
        lookup_url = (f'https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?'
                      f'id={usi}')
        lookup_request = requests.get(lookup_url)
        lookup_request.raise_for_status()
        for spectrum_file in lookup_request.json()['row_data']:
            if any(spectrum_file['file_descriptor'].lower().endswith(extension)
                   for extension in ['mzml', 'mzxml', 'mgf']):
                request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                               f'DownloadResultFile?'
                               f'task=4f2ac74ea114401787a7e96e143bb4a1&'
                               f'invoke=annotatedSpectrumImageText&block=0&'
                               f'file=FILE->{spectrum_file["file_descriptor"]}'
                               f'&scan={scan}&peptide=*..*&force=false&'
                               f'format=JSON&uploadfile=True')
                try:
                    spectrum_request = requests.get(request_url)
                    spectrum_request.raise_for_status()
                    spectrum_dict = spectrum_request.json()
                except (requests.exceptions.HTTPError,
                        json.decoder.JSONDecodeError):
                    continue
                mz, intensity = zip(*spectrum_dict['peaks'])
                if 'precursor' in spectrum_dict:
                    precursor_mz = float(
                        spectrum_dict['precursor'].get('mz', 0))
                    charge = int(spectrum_dict['precursor'].get('charge', 0))
                else:
                    precursor_mz, charge = 0, 0
                if dataset_identifier.lower().startswith('pxd'):
                    source_link = (
                        f'http://proteomecentral.proteomexchange.org/'
                        f'cgi/GetDataset?ID={dataset_identifier}')
                else:
                    source_link = (f'https://massive.ucsd.edu/ProteoSAFe/'
                                   f'QueryMSV?id={dataset_identifier}')

                return sus.MsmsSpectrum(usi, precursor_mz, charge, mz,
                                        intensity), source_link
    except requests.exceptions.HTTPError:
        pass
    raise ValueError('Unsupported/unknown USI')


# Parse MOTIFDB from ms2lda.org.
def _parse_motifdb(usi):
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != 'accession':
        raise ValueError('Currently supported MOTIFDB index flags: accession')
    index = match.group(4)
    try:
        lookup_request = requests.get(f'{MOTIFDB_SERVER}get_motif/{index}')
        lookup_request.raise_for_status()
        mz, intensity = zip(*json.loads(lookup_request.text))
        source_link = f'http://ms2lda.org/motifdb/motif/{index}/'
        return sus.MsmsSpectrum(usi, 0, 0, mz, intensity), source_link
    except requests.exceptions.HTTPError:
        raise ValueError('Unknown MOTIFDB USI')
