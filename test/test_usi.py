import sys
sys.path.insert(0, "..")
import parsing

def test_gnps():
    parsing.parse_usi("mzspec:GNPSTASK-c95481f0c53d42e78a61bf899e9f9adb:spectra/specs_ms.mgf:scan:1943")

def test_msv():
    parsing.parse_usi("mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555")

def test_mtbls():
    parsing.parse_usi("mzspec:MTBLS38:(-)-epigallocatechin:scan:2")
    parsing.parse_usi("mzspec:MSV000082791:(-)-epigallocatechin:scan:2")

def test_pxd():
    parsing.parse_usi("mzspec:PXD000561:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555")

def test_massbank():
    parsing.parse_usi("mzdata:MASSBANK:BSU00002")

def test_gnpslib():
    parsing.parse_usi("mzspec:GNPSLIBRARY:CCMSLIB00005436077")

def test_motifdb():
    parsing.parse_usi("mzspec:MOTIFDB:motif:171163")
