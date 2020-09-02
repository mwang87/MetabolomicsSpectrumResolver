import sys
sys.path.insert(0, '..')

import pytest

import parsing

from usi_test_data import usis_to_test


def test_parse_usi():
    # ValueError will be thrown if invalid USI.
    for usi in usis_to_test:
        parsing.parse_usi(usi)
        if any(collection in usi for collection in
               ['MASSIVEKB', 'GNPS', 'MASSBANK', 'MS2LDA', 'MOTIFDB']):
            parsing.parse_usi(usi.replace('mzspec', 'mzdraft'))


def test_parse_usi_invalid():
    with pytest.raises(ValueError):
        parsing.parse_usi('this:is:an:invalid:usi')
    # Invalid preamble.
    # FIXME: Exception not thrown because of legacy parsing.
    # with pytest.raises(ValueError):
    #     parsing.parse_usi('not_mzspec:PXD000561:'
    #                       'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    # Invalid collection.
    with pytest.raises(ValueError):
        parsing.parse_usi('mzspec:PXD000000000:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    with pytest.raises(ValueError):
        parsing.parse_usi('mzspec:RANDOM666:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    # Invalid index.
    # FIXME: Exception not thrown because of legacy parsing.
    # with pytest.raises(ValueError):
    #     parsing.parse_usi('mzspec:PXD000561:'
    #                       'Adult_Frontalcortex_bRP_Elite_85_f09:'
    #                       'not_scan:17555')
    # Missing index.
    with pytest.raises(ValueError):
        parsing.parse_usi('mzspec:PXD000561:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:')


def test_parse_gnps_task():
    usi = ('mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/'
           'specs_ms.mgf:scan:1943')
    parsing.parse_usi(usi)
    # Invalid task pattern.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':TASK-', ':TASK-666'))
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':scan:', ':index:'))
    # Invalid file name.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace('specs_ms.mgf', 'nonexisting.mgf'))
    # Invalid scan number.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':1943', ':this_scan_does_not_exist'))


def test_parse_gnps_library():
    usi = 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077'
    parsing.parse_usi(usi)
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    # Invalid accession.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':CCMSLIB00005436077',
                                      ':this_accession_does_not_exist'))


def test_parse_massbank():
    usi = 'mzspec:MASSBANK::accession:SM858102'
    parsing.parse_usi(usi)
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    # Invalid accession.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':SM858102',
                                      ':this_accession_does_not_exist'))


def test_parse_ms2lda():
    usi = 'mzspec:MS2LDA:TASK-190:accession:270684'
    parsing.parse_usi(usi)
    # Invalid task pattern.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':TASK-', ':TASK-bla'))
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    # Invalid experiment ID.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':TASK-190', ':TASK-666666666'))
    # Invalid document ID.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':270684',
                                      ':this_document_does_not_exist'))


def test_parse_msv_pxd():
    usi = 'mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555'
    parsing.parse_usi(usi)
    # Invalid collection.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':MSV000079514:', ':MSV666666666:'))
    # Invalid file name.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace('Adult_Frontalcortex_bRP_Elite_85_f09',
                                      'this_filename_does_not_exist'))
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':scan:', ':index:'))
    # Invalid scan number.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':17555', ':this_scan_does_not_exist'))


def test_parse_motifdb():
    usi = 'mzspec:MOTIFDB::accession:171163'
    parsing.parse_usi(usi)
    # Invalid index flag.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    # Invalid index.
    with pytest.raises(ValueError):
        parsing.parse_usi(usi.replace(':171163', ':this_index_does_not_exist'))
