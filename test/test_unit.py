import sys
sys.path.insert(0, '..')

import pytest
import werkzeug.datastructures

import parsing
import views

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


def _get_plotting_args(**kwargs):
    plotting_args = views.default_plotting_args.copy()
    plotting_args['mz_min'], plotting_args['mz_max'] = 50, 500
    plotting_args['max_intensity'] = plotting_args['max_intensity_unlabeled']
    del plotting_args['annotate_peaks']
    for key, value in kwargs.items():
        plotting_args[key] = value
    return werkzeug.datastructures.ImmutableMultiDict(plotting_args)


def test_get_plotting_args_invalid_figsize():
    plotting_args = views._get_plotting_args(_get_plotting_args(width=-1))
    assert plotting_args['width'] == views.default_plotting_args['width']
    plotting_args = views._get_plotting_args(_get_plotting_args(height=-1))
    assert plotting_args['height'] == views.default_plotting_args['height']
    plotting_args = views._get_plotting_args(_get_plotting_args(width=-1),
                                             mirror=True)
    assert plotting_args['width'] == views.default_plotting_args['width']
    plotting_args = views._get_plotting_args(_get_plotting_args(height=-1),
                                             mirror=True)
    assert plotting_args['height'] == views.default_plotting_args['height']


def test_get_plotting_args_invalid_mz_range():
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_min=-100))
    assert 'mz_min' not in plotting_args
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_max=-100))
    assert 'mz_max' not in plotting_args
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_min=-100),
                                             mirror=True)
    assert 'mz_min' not in plotting_args
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_max=-100),
                                             mirror=True)
    assert 'mz_max' not in plotting_args


def test_get_plotting_args_invalid_max_intensity():
    plotting_args = views._get_plotting_args(_get_plotting_args(
        max_intensity=-1))
    assert (plotting_args['max_intensity']
            == views.default_plotting_args['max_intensity_labeled'])
    plotting_args = views._get_plotting_args(_get_plotting_args(
        max_intensity=-1), mirror=True)
    assert (plotting_args['max_intensity']
            == views.default_plotting_args['max_intensity_mirror_labeled'])


def test_get_plotting_args_invalid_annotate_precision():
    plotting_args = views._get_plotting_args(_get_plotting_args(
        annotate_precision=-1))
    assert (plotting_args['annotate_precision']
            == views.default_plotting_args['annotate_precision'])
