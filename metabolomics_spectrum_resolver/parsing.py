import datetime
import json
import re
from typing import Tuple

import requests
import pandas as pd
from io import StringIO
import urllib.parse
import spectrum_utils.spectrum as sus
import splash

from metabolomics_spectrum_resolver.error import UsiError

timeout = 45  # seconds

MS2LDA_SERVER = "http://ms2lda.org/basicviz/"
MOTIFDB_SERVER = "http://ms2lda.org/motifdb/"
MASSBANK_SERVER = "https://massbank.us/rest/spectra/"

# USI specification: http://www.psidev.info/usi
usi_pattern = re.compile(
    # mzspec preamble
    r"^mzspec"
    # collection identifier
    # Proteomics collection identifiers: PXDnnnnnn, MSVnnnnnnnnn, RPXDnnnnnn,
    #                                    PXLnnnnnn
    # Unofficial: MASSIVEKB
    # https://github.com/HUPO-PSI/usi/blob/master/CollectionIdentifiers.md
    r":(MSV\d{9}|PXD\d{6}|PXL\d{6}|RPXD\d{6}|ST\d{6}|MassIVE)"
    # msRun identifier
    r":(.*)"
    # index flag
    r":(scan|index|nativeId|trace)"
    # index number
    r":([^:]+)"
    # optional spectrum interpretation
    r"(:.+)?$",
    flags=re.IGNORECASE,
)
# OR: Metabolomics USIs.
usi_metabolomics_pattern = re.compile(
    # mzspec preamble
    r"^mzspec"
    # collection identifier
    # Unofficial proteomics spectral library identifier: MASSIVEKB
    # Metabolomics collection identifiers: GNPS, MASSBANK, MS2LDA, MOTIFDB
    r":(MASSIVEKB|GNPS|GNPS2|MASSBANK|MS2LDA|MOTIFDB|TINYMASS)"
    # msRun identifier
    r":(.*)"
    # index flag
    r":(scan|index|nativeId|trace|accession)"
    # index number
    r":([^:]+)"
    # optional spectrum interpretation
    r"(:.+)?$",
    flags=re.IGNORECASE,
)
# Legacy metabolomics USIs.
usi_legacy_pattern = re.compile(
    # Legacy GNPS task.
    r"^((?:mzspec|mzdraft):GNPSTASK-[a-z0-9]{32}:.+:scan:\d+)|"
    # Legacy GNPS library.
    r"((?:mzspec|mzdraft):GNPSLIBRARY:CCMSLIB\d+)|"
    # Legacy MassBank.
    r"((?:mzspec|mzdraft):MASSBANK:[^:]+)|"
    # Legacy MotifDB.
    r"((?:mzspec|mzdraft):MOTIFDB:motif:[^:]+)|"
    # Legacy MS2LDA.
    r"((?:mzspec|mzdraft):MS2LDATASK-[^:]+:document:[^:]+)$",
    flags=re.IGNORECASE,
)
gnps_task_pattern = re.compile(
    r"^TASK-([a-z0-9]{32})-(.+)$", flags=re.IGNORECASE
)
ms2lda_task_pattern = re.compile(r"^TASK-(\d+)$", flags=re.IGNORECASE)

splash_builder = splash.Splash()


def parse_usi(usi: str) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of the `MsmsSpectrum`, its source link, and its SPLASH.
    """
    match = _match_usi(usi)
    try:
        collection = match.group(1).lower()
        annotation = match.group(5)
        # Send all proteomics USIs (by definition all annotated USIs) to
        # MassIVE.
        # mzdraft USIs are assumed to also use ProForma notation. If this
        # changes, be sure to change this logic.
        if (
            annotation is not None
            or collection.startswith("msv")
            or collection.startswith("pxd")
            or collection.startswith("pxl")
            or collection.startswith("rpxd")
            or collection == "massivekb"
            or collection == "massive"
        ):
            spectrum, source_link = _parse_msv_pxd(usi)
        elif collection == "gnps":
            spectrum, source_link = _parse_gnps(usi)
        elif collection == "gnps2":
            spectrum, source_link = _parse_gnps2(usi)
        elif collection == "massbank":
            spectrum, source_link = _parse_massbank(usi)
        elif collection == "ms2lda":
            spectrum, source_link = _parse_ms2lda(usi)
        elif collection == "motifdb":
            spectrum, source_link = _parse_motifdb(usi)
        elif collection.startswith("st"):
            spectrum, source_link = _parse_metabolomics_workbench(usi)
        elif collection.startswith("tinymass"):
            spectrum, source_link = _parse_tinymass(usi)
        else:
            raise UsiError(f"Unknown USI collection: {match.group(1)}", 400)
        splash_key = splash_builder.splash(
            splash.Spectrum(
                list(zip(spectrum.mz, spectrum.intensity)),
                splash.SpectrumType.MS,
            )
        )
        return spectrum, source_link, splash_key
    except requests.exceptions.Timeout:
        raise UsiError(
            "Timeout while retrieving the USI from an external " "resource",
            504,
        )


def parse_spectrum(spectrum: dict) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Parse the spectrum PROXI object into a MsmsSpectrum object.

    Parameters
    ----------
    spectrum : dict
        The JSON dict for a spectrum in PROXI format.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of the `MsmsSpectrum`, its source link, and its SPLASH.
    """

    source_link = "Peak Input"

    mz, intensity = spectrum["mzs"], spectrum["intensities"]

    precursor_mz = 0
    charge = 0
    peptide = None
    peptide_clean = None

    for attribute in spectrum["attributes"]:
        # isolation window target m/z
        if attribute["accession"] == "MS:1000827":
            precursor_mz = float(attribute["value"])
        # selected ion m/z
        elif attribute["accession"] == "MS:1000744":
            precursor_mz = float(attribute["value"])
        # charge state
        elif attribute["accession"] == "MS:1000041":
            charge = int(attribute["value"])
        # peptidoform
        elif attribute["accession"] == "MS:1003049":
            peptide = attribute["value"]
        # unmodified peptide sequence
        elif attribute["accession"] == "MS:1000888":
            peptide_clean = attribute["value"]

    # Parse the peptide if available.
    try:
        peptide, peptide_clean, modifications = _parse_sequence(
            peptide, peptide_clean
        )

        spectrum = sus.MsmsSpectrum(
            spectrum.get("usi", "Peak Input"),
            precursor_mz,
            charge,
            mz,
            intensity,
            peptide=peptide_clean,
            modifications=modifications,
        )

    except (TypeError, KeyError):
        spectrum = sus.MsmsSpectrum(
            spectrum.get("usi", "Peak Input"),
            precursor_mz,
            charge,
            mz,
            intensity,
        )

    splash_key = splash_builder.splash(
        splash.Spectrum(
            list(zip(spectrum.mz, spectrum.intensity)),
            splash.SpectrumType.MS,
        )
    )

    return spectrum, source_link, splash_key


def parse_usi_or_spectrum(
    usi: str, spectrum_dict: dict
) -> Tuple[sus.MsmsSpectrum, str, str]:

    if usi and usi != "":
        spectrum_output = parse_usi(usi)
    elif spectrum_dict:
        spectrum_output = parse_spectrum(spectrum_dict)
    else:
        raise UsiError("Neither USI nor peaks given as input")

    return spectrum_output


def _match_usi(usi: str) -> re.Match:
    """
    Parse a USI into its constituent parts.

    Parameters
    ----------
    usi : str
        The USI to be parsed.

    Returns
    -------
    re.Match
        The parsed USI.

    Raises
    ------
    UsiError
        If the USI could not be parsed because it is incorrectly formatted.
    """
    # Translate legacy USIs if necessary.
    if usi_legacy_pattern.match(usi) is not None:
        usi = _convert_legacy_usi(usi)
    # First try matching as an official USI, then as a metabolomics USI.
    match = usi_pattern.match(usi)
    if match is None:
        match = usi_metabolomics_pattern.match(usi)
    if match is None:
        raise UsiError(f"Incorrectly formatted USI: {usi}", 400)
    return match


def _convert_legacy_usi(usi: str) -> str:
    """
    Convert a legacy format metabolomics USI to the proper metabolomics USI
    format.

    Parameters
    ----------
    usi : str
        The legacy metabolomics USI to convert.

    Returns
    -------
    str
        The updated metabolomics USI.

    Raises
    ------
    UsiError
        If the legacy USI is incorrectly formatted.
    """
    # Convert GNPS task legacy USI.
    match = re.compile(
        r"^(?:mzspec|mzdraft):GNPSTASK-([a-z0-9]{32}):(.+):scan:(\d+)$",
        flags=re.IGNORECASE,
    ).match(usi)
    if match is not None:
        return f"mzspec:GNPS:TASK-{match[1]}-{match[2]}:scan:{match[3]}"
    # Convert GNPS library legacy USI.
    match = re.compile(
        r"^(?:mzspec|mzdraft):GNPSLIBRARY:(CCMSLIB\d+)$", flags=re.IGNORECASE
    ).match(usi)
    if match is not None:
        return f"mzspec:GNPS:GNPS-LIBRARY:accession:{match[1]}"
    # Convert MassBank legacy USI.
    match = re.compile(
        r"^(?:mzspec|mzdraft):MASSBANK:([^:]+)$", flags=re.IGNORECASE
    ).match(usi)
    if match is not None:
        return f"mzspec:MASSBANK::accession:{match[1]}"
    # Convert MotifDB legacy USI.
    match = re.compile(
        r"^(?:mzspec|mzdraft):MOTIFDB:motif:([^:]+)$", flags=re.IGNORECASE
    ).match(usi)
    if match is not None:
        return f"mzspec:MOTIFDB::accession:{match[1]}"
    # Convert MS2LDA legacy USI.
    match = re.compile(
        r"^(?:mzspec|mzdraft):MS2LDATASK-([^:]+):document:([^:]+)$",
        flags=re.IGNORECASE,
    ).match(usi)
    if match is not None:
        return f"mzspec:MS2LDA:TASK-{match[1]}:accession:{match[2]}"
    # Give an error on unknown legacy USI.
    raise UsiError(f"Incorrectly formatted legacy USI: {usi}", 400)


# Parse GNPS tasks or library spectra.
def _parse_gnps(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    ms_run = match.group(2)
    if ms_run.lower().startswith("task"):
        return _parse_gnps_task(usi)
    else:
        return _parse_gnps_library(usi)

def _parse_gnps2(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    ms_run = match.group(2)
    if ms_run.lower().startswith("task"):
        return _parse_gnps2_task(usi)

# Parse GNPS clustered spectra in Molecular Networking.
def _parse_gnps_task(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    gnps_task_match = gnps_task_pattern.match(match.group(2))
    if gnps_task_match is None:
        raise UsiError("Incorrectly formatted GNPS task", 400)
    task = gnps_task_match.group(1)
    filename = gnps_task_match.group(2)
    index_flag = match.group(3)
    if index_flag.lower() != "scan":
        raise UsiError("Currently supported GNPS TASK index flags: scan", 400)
    scan = match.group(4)

    try:
        request_url = (
            f"https://gnps.ucsd.edu/ProteoSAFe/DownloadResultFile?"
            f"task={task}&invoke=annotatedSpectrumImageText&block=0"
            f"&file=FILE->{filename}&scan={scan}&peptide=*..*&"
            f"force=false&_=1561457932129&format=JSON"
        )
        lookup_request = requests.get(request_url, timeout=timeout)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        mz, intensity = zip(*spectrum_dict["peaks"])
        source_link = (
            f"https://gnps.ucsd.edu/ProteoSAFe/status.jsp?" f"task={task}"
        )
        if "precursor" in spectrum_dict:
            precursor_mz = float(spectrum_dict["precursor"].get("mz", 0))
            charge = int(spectrum_dict["precursor"].get("charge", 0))
        else:
            precursor_mz, charge = 0, 0

        spectrum = sus.MsmsSpectrum(usi, precursor_mz, charge, mz, intensity)
        return spectrum, source_link
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise UsiError("Unknown GNPS task USI", 404)


# Parse GNPS2 task spectra
def _parse_gnps2_task(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    gnps_task_match = gnps_task_pattern.match(match.group(2))
    if gnps_task_match is None:
        raise UsiError("Incorrectly formatted GNPS2 task", 400)
    task = gnps_task_match.group(1)
    filename = gnps_task_match.group(2)
    index_flag = match.group(3)
    if index_flag.lower() != "scan":
        raise UsiError("Currently supported GNPS2 TASK index flags: scan", 400)
    scan = match.group(4)

    try:
        request_url = (
            f"https://gnps2.org/spectrumpeaks?format=json&usi={usi}"
        )
        lookup_request = requests.get(request_url, timeout=timeout)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        mz, intensity = zip(*spectrum_dict["peaks"])
        source_link = (
            f"https://gnps2.org/status?task={task}"
        )
        if "precursor_mz" in spectrum_dict:
            precursor_mz = float(spectrum_dict["precursor_mz"])
            charge = 0
        else:
            precursor_mz, charge = 0, 0

        spectrum = sus.MsmsSpectrum(usi, precursor_mz, charge, mz, intensity)
        return spectrum, source_link
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise UsiError("Unknown GNPS2 task USI", 404)

# Parse TINYMASS task spectra
def _parse_tinymass(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)

    try:
        request_url = (
            f"https://tinymass.gnps2.org/resolve?usi={usi}"
        )
        lookup_request = requests.get(request_url, timeout=timeout)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        mz, intensity = zip(*spectrum_dict["peaks"])
        source_link = (
            f"https://tinymass.gnps2.org/resolve?usi={usi}"
        )
        if "precursor" in spectrum_dict:
            precursor_mz = float(spectrum_dict["precursor"])
            charge = 0
        else:
            precursor_mz, charge = 0, 0

        spectrum = sus.MsmsSpectrum(usi, precursor_mz, charge, mz, intensity)
        return spectrum, source_link
    except (requests.exceptions.HTTPError, json.decoder.JSONDecodeError):
        raise UsiError("Unknown Tiny Mass task USI", 404)

# Parse GNPS library.
def _parse_gnps_library(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != "accession":
        raise UsiError(
            "Currently supported GNPS library index flags: accession", 400
        )
    index = match.group(4)
    try:
        request_url = (
            f"https://external.gnps2.org/"
            f"gnpsspectrum?SpectrumID={index}"
        )
        lookup_request = requests.get(request_url, timeout=timeout)
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        if spectrum_dict["spectruminfo"]["peaks_json"] == "null":
            raise UsiError("Unknown GNPS library USI", 404)
        mz, intensity = zip(
            *json.loads(spectrum_dict["spectruminfo"]["peaks_json"])
        )
        source_link = (
            f"https://gnps.ucsd.edu/ProteoSAFe/"
            f"gnpslibraryspectrum.jsp?SpectrumID={index}"
        )

        # Use the most up-to-date spectrum annotation.
        annotations = sorted(
            spectrum_dict["annotations"],
            key=lambda annotation: datetime.datetime.strptime(
                annotation["create_time"], "%Y-%m-%d %H:%M:%S.%f"
            ),
            reverse=True,
        )[0]
        spectrum = sus.MsmsSpectrum(
            usi,
            float(annotations["Precursor_MZ"]),
            int(annotations["Charge"]),
            mz,
            intensity,
        )
        return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise UsiError("Unknown GNPS library USI", 404)


# Parse MassBank entry.
def _parse_massbank(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != "accession":
        raise UsiError(
            "Currently supported MassBank index flags: accession", 400
        )
    index = match.group(4)
    # Clean up the new MassBank accessions if necessary.
    massbank_accession = re.match(
        r"MSBNK-[A-Z0-9_]{1,32}-([A-Z0-9_]{1,64})", index
    )
    if massbank_accession is not None:
        index = massbank_accession.group(1)
    try:
        lookup_request = requests.get(
            f"{MASSBANK_SERVER}{index}", timeout=timeout
        )
        lookup_request.raise_for_status()
        spectrum_dict = lookup_request.json()
        mz, intensity = [], []
        for peak in spectrum_dict["spectrum"].split():
            peak_mz, peak_intensity = peak.split(":")
            mz.append(float(peak_mz))
            intensity.append(float(peak_intensity))
        precursor_mz = 0
        for metadata in spectrum_dict["metaData"]:
            if metadata["name"] == "precursor m/z":
                precursor_mz = float(metadata["value"])
                break
        source_link = (
            f"https://massbank.eu/MassBank/" f"RecordDisplay.jsp?id={index}"
        )

        spectrum = sus.MsmsSpectrum(usi, precursor_mz, 0, mz, intensity)
        return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise UsiError("Unknown MassBank USI", 404)


# Parse MS2LDA from ms2lda.org.
def _parse_ms2lda(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    ms2lda_task_match = ms2lda_task_pattern.match(match.group(2))
    if ms2lda_task_match is None:
        raise UsiError("Incorrectly formatted MS2LDA task", 400)
    experiment_id = ms2lda_task_match.group(1)
    index_flag = match.group(3)
    if index_flag.lower() != "accession":
        raise UsiError(
            "Currently supported MS2LDA index flags: accession", 400
        )
    index = match.group(4)
    try:
        lookup_request = requests.get(
            f"{MS2LDA_SERVER}get_doc/?experiment_id={experiment_id}"
            f"&document_id={index}",
            timeout=timeout,
        )
        lookup_request.raise_for_status()
        spectrum_dict = json.loads(lookup_request.text)
        if "error" in spectrum_dict:
            raise UsiError(f'MS2LDA error: {spectrum_dict["error"]}', 404)
        mz, intensity = zip(*spectrum_dict["peaks"])
        source_link = f"http://ms2lda.org/basicviz/show_doc/{index}/"

        spectrum = sus.MsmsSpectrum(
            usi, float(spectrum_dict["precursor_mz"]), 0, mz, intensity
        )
        return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise UsiError("Unknown MS2LDA USI", 404)


# Parse MSV or PXD library.
def _parse_msv_pxd(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    dataset_identifier = match.group(1)
    index_flag = match.group(3)
    if index_flag.lower() != "scan":
        raise UsiError("Currently supported MassIVE index flags: scan", 400)
    scan = match.group(4)
    try:
        lookup_url = (
            f"https://massive.ucsd.edu/ProteoSAFe/"
            f"QuerySpectrum?id={urllib.parse.quote_plus(usi)}"
        )
        lookup_request = requests.get(lookup_url, timeout=timeout)
        lookup_request.raise_for_status()
        lookup_json = lookup_request.json()
        for spectrum_file in lookup_json["row_data"]:
            # Checking if its an actual file we can resolve or if MSV will go to PX directly
            if any(
                spectrum_file["file_descriptor"].lower().endswith(extension)
                for extension in ["mzml", "mzxml", "mgf"]
            ) or spectrum_file["file_descriptor"].startswith("f.ProteomeCentral"):
                file_descriptor = spectrum_file['file_descriptor']
                if file_descriptor.startswith("f."):
                    file_descriptor = file_descriptor[2:]

                peaks_request_url = (
                    f"https://massive.ucsd.edu/ProteoSAFe/"
                    f"DownloadResultFile?"
                    f"task=4f2ac74ea114401787a7e96e143bb4a1&"
                    f"invoke=annotatedSpectrumImageText&block=0&file=FILE->"
                    f"{urllib.parse.quote(file_descriptor)}"
                    f"&scan={scan}&peptide=*..*&force=false&"
                    f"format=JSON&uploadfile=True"
                )
                
                try:
                    spectrum_request = requests.get(
                        peaks_request_url, timeout=timeout
                    )
                    spectrum_request.raise_for_status()
                    spectrum_dict = spectrum_request.json()
                except (
                    requests.exceptions.HTTPError,
                    json.decoder.JSONDecodeError,
                ):
                    continue
                if len(spectrum_dict["peaks"]) == 0:
                    continue
                mz, intensity = zip(*spectrum_dict["peaks"])
                if "precursor" in spectrum_dict:
                    precursor_mz = float(
                        spectrum_dict["precursor"].get("mz", 0)
                    )
                    charge = int(spectrum_dict["precursor"].get("charge", 0))
                else:
                    precursor_mz, charge = 0, 0
                if dataset_identifier.lower().startswith("pxd"):
                    source_link = (
                        f"http://proteomecentral.proteomexchange.org/"
                        f"cgi/GetDataset?ID={dataset_identifier}"
                    )
                else:
                    source_link = (
                        f"https://massive.ucsd.edu/ProteoSAFe/"
                        f"QueryMSV?id={dataset_identifier}"
                    )

                # Parse the peptide if available.
                try:
                    # Get the peptide information from resolution,
                    # this dereferences proforma.
                    peptide_clean = lookup_json["usi_components"]["peptide"]
                    peptide = lookup_json["usi_components"]["variant"]
                    charge = int(lookup_json["usi_components"]["charge"])

                    peptide, peptide_clean, modifications = _parse_sequence(
                        peptide, peptide_clean
                    )
                    spectrum = sus.MsmsSpectrum(
                        usi,
                        precursor_mz,
                        charge,
                        mz,
                        intensity,
                        peptide=peptide_clean,
                        modifications=modifications,
                    )
                except (TypeError, KeyError):
                    spectrum = sus.MsmsSpectrum(
                        usi, precursor_mz, charge, mz, intensity
                    )

                return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise
        pass
    raise UsiError("Unsupported/unknown USI", 404)


# Parse MOTIFDB from ms2lda.org.
def _parse_motifdb(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    index_flag = match.group(3)
    if index_flag.lower() != "accession":
        raise UsiError(
            "Currently supported MOTIFDB index flags: accession", 400
        )
    index = match.group(4)
    try:
        lookup_request = requests.get(
            f"{MOTIFDB_SERVER}get_motif/{index}", timeout=timeout
        )
        lookup_request.raise_for_status()
        mz, intensity = zip(*json.loads(lookup_request.text))
        source_link = f"http://ms2lda.org/motifdb/motif/{index}/"

        spectrum = sus.MsmsSpectrum(usi, 0, 0, mz, intensity)
        return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise UsiError("Unknown MOTIFDB USI", 404)


# Parse GNPS library.
def _parse_metabolomics_workbench(usi: str) -> Tuple[sus.MsmsSpectrum, str]:
    match = _match_usi(usi)
    accession = match.group(1)
    filename = match.group(2)
    index_flag = match.group(3)
    index = match.group(4)

    if index_flag.lower() != "scan":
        raise UsiError(
            "Currently supported MW index flags: scan", 400
        )
    try:
        request_url = (
            f"https://www.metabolomicsworkbench.org/"
            f"data/ms2.php?A={accession}.zip"
            f"&F={urllib.parse.quote_plus(filename)}&S={index}"
        )

        # TODO: Do some extra exception handling if we don't find the filename directly. We might need to his another API to get the full filename
        # Given the just the basename
        
        lookup_request = requests.get(request_url, timeout=timeout)
        lookup_request.raise_for_status()

        response_text = lookup_request.text
        response_text = (response_text.replace("<pre>", "").replace("</pre></br>", "").lstrip().rstrip())

        # Parsing the MW Response
        precursor_mz = float(response_text.split("\n")[0].split(":")[-1].replace("\"", ""))
        charge = int(response_text.split("\n")[2].split(":")[-1].replace("\"", ""))
        peaks_df = pd.read_csv(StringIO(response_text), sep=r" +", skiprows=4)
        mz = list(peaks_df["m/z"])
        intensity = list(peaks_df["intensity"])

        source_link = (
            f"https://www.metabolomicsworkbench.org/"
            f"data/DRCCMetadata.php?Mode=Study&StudyID={accession}&StudyType=MS&ResultType=1"
        )

        spectrum = sus.MsmsSpectrum(
            usi,
            float(precursor_mz),
            int(charge),
            mz,
            intensity,
        )
        return spectrum, source_link
    except requests.exceptions.HTTPError:
        raise UsiError("Unknown MW USI", 404)

def _parse_sequence(peptide: str, peptide_clean: str) -> Tuple[str, str, list]:
    # Parse out gapped sequence (e.g. X+129.04259), faking it
    # with Glycine as the base residue and adding more mods to
    # it.
    gapmod_pattern = re.compile("X[+][0-9.]*")
    transformed_peptide = peptide
    for match in gapmod_pattern.finditer(peptide):
        gap_mass = float(match.group().replace("X", ""))
        # Fake the gap with glycine.
        transformed_peptide = transformed_peptide.replace(
            match.group(), f"G{gap_mass - 57.021463735:+}"
        )
    peptide_clean = peptide_clean.replace("X", "G")
    peptide = transformed_peptide

    # Parse out modifications.
    mod_pattern = re.compile("[-+][0-9.]*")
    modifications, previous_mod_len = {}, 0
    for match in mod_pattern.finditer(peptide):
        found_pos = match.start()
        found_len = len(match.group())
        i = max(0, found_pos - previous_mod_len - 1)
        modifications[i] = float(match.group())
        previous_mod_len += found_len
    return peptide, peptide_clean, modifications
