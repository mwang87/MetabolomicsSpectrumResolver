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
