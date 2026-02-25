import functools
import json
import sys

sys.path.insert(0, "../")  # Add the parent directory to the path

from metabolomics_spectrum_resolver import parsing, similarity, views



def debug():
    usi = "mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00017443251"
    # Parse the USI
    parsed_usi = parsing.parse_usi(usi)
    print("Parsed USI:", parsed_usi)


if __name__ == "__main__":
    debug()