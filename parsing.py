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
    '(:.+)?$'
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
    '(:.+)?$'
)
gnps_task_pattern = re.compile('^TASK-([a-z0-9]{32})-(.+)$')
ms2lda_task_pattern = re.compile('^TASK-(\d+)$')

def _match_usi(usi):
    # First try matching as an official USI, then as a metabolomics draft USI.
    match = usi_pattern.match(usi)
    if match is None:
        match = usi_pattern_draft.match(usi)
    if match is None:
        raise ValueError('Incorrectly formatted USI')
    return match


@functools.lru_cache(100)
def parse_usi(usi):
    try:
        match = _match_usi(usi)
        collection = match.group(1)
        # Send all proteomics USIs to MassIVE.
        if (collection.startswith('MSV') or
                collection.startswith('PXD') or
                collection.startswith('PXL') or
                collection.startswith('RPXD') or
                collection == 'MASSIVEKB'):
            return _parse_msv_pxd(usi)
        elif collection == 'GNPS':
            return _parse_gnps(usi)
        elif collection == 'MASSBANK':
            return _parse_massbank(usi)
        elif collection == 'MS2LDA':
            return _parse_ms2lda(usi)
        elif collection == 'MOTIFDB':
            return _parse_motifdb(usi)
        else:
            raise ValueError(f'Unknown USI collection: {collection}')
    except Exception as e:
        # Lets try to parse the legacy
        try:
            return parsing_legacy.parse_usi_legacy(usi)
        except:
            print("XXX")
            raise e


# Parse GNPS tasks or library spectra.
def _parse_gnps(usi):
    match = _match_usi(usi)
    ms_run = match.group(2)
    if ms_run.startswith('TASK'):
        return _parse_gnps_task(usi)
    else:
        return _parse_gnps_library(usi)


# Parse GNPS clustered spectra in Molecular Networking.
def _parse_gnps_task(usi):
    match = _match_usi(usi)
    gnps_task_match = gnps_task_pattern.match(match.group(2))
    task = gnps_task_match.group(1)
    filename = gnps_task_match.group(2)
    index_flag = match.group(3)
    if index_flag != 'scan':
        raise ValueError('Currently supported GNPS TASK index flags: scan')
    scan = match.group(4)
    
    # Performing Query
    try:
        request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?'
                       f'task={task}&invoke=annotatedSpectrumImageText&block=0&'
                       f'file=FILE->{filename}&scan={scan}&peptide=*..*&'
                       f'force=false&_=1561457932129&format=JSON')
        spectrum_dict = requests.get(request_url).json()
        mz, intensity =  zip(*spectrum_dict['peaks'])
        source_link = f'https://gnps.ucsd.edu/ProteoSAFe/status.jsp?task={task}'
        precursor_mz = 0
        charge = 1
        
        try:
            precursor_mz = spectrum_dict['precursor']['mz']
            charge = spectrum_dict['precursor']['charge']
        except:
            pass
        
        return sus.MsmsSpectrum(usi, 0, 0, mz, intensity), source_link
    except requests.exceptions.HTTPError:
        raise ValueError('Unknown GNPS task USI')
    
# Parse GNPS library.
def _parse_gnps_library(usi):
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag != 'accession':
        raise ValueError('Currently supported GNPS library index flags: '
                         'accession')
    index = match.group(4)
    try:
        request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                       f'SpectrumCommentServlet?SpectrumID={index}')
        lookup_request = requests.get(request_url)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
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
    if index_flag != 'accession':
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
    experiment_id = ms2lda_task_match.group(1)
    index_flag = match.group(3)
    if index_flag != 'accession':
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
    tokens = usi.split(':')
    dataset_identifier = tokens[1]
    filename = tokens[2]
    scan = tokens[4]
    lookup_url = (f'https://massive.ucsd.edu/ProteoSAFe/QuerySpectrum?'
                  f'id=mzspec:{dataset_identifier}:{filename}:scan:{scan}')
    usi_resolvable = False
    for spectrum_file in requests.get(lookup_url).json()['row_data']:
        try:
            usi_resolvable = any(
                spectrum_file['file_descriptor'].lower().endswith(extension)
                for extension in ['mzml', 'mzxml', 'mgf'])
            if usi_resolvable:
                request_url = (f'https://gnps.ucsd.edu/ProteoSAFe/'
                               f'DownloadResultFile?'
                               f'task=4f2ac74ea114401787a7e96e143bb4a1&'
                               f'invoke=annotatedSpectrumImageText&block=0&'
                               f'file=FILE->{spectrum_file["file_descriptor"]}'
                               f'&scan={scan}&peptide=*..*&force=false&'
                               f'format=JSON&uploadfile=True')
                spectrum_dict = requests.get(request_url).json()
                mz, intensity = zip(*spectrum_dict['peaks'])

                precursor_mz = 0
                charge = 1

                try:
                    charge = int(spectrum_dict['precursor']['charge'])
                    precursor_mz = float(spectrum_dict['precursor']['mz'])
                except:
                    pass

                if dataset_identifier.startswith('PXD'):
                    source_link = (
                        f'http://proteomecentral.proteomexchange.org/'
                        f'cgi/GetDataset?ID={dataset_identifier}')
                else:
                    source_link = (f'https://massive.ucsd.edu/ProteoSAFe/'
                                   f'QueryMSV?id={dataset_identifier}')

                return sus.MsmsSpectrum(usi, precursor_mz, charge, mz,
                                        intensity), source_link
        except:
            pass
    if usi_resolvable:
        raise ValueError('Cannot resolve USI')
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
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag != 'accession':
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
