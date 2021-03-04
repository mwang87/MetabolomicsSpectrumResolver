import functools
import json
import sys
import unittest.mock
sys.path.insert(0, '..')

import numpy as np
import pytest
import requests
import werkzeug.datastructures
from spectrum_utils import spectrum as sus

import parsing
import views
from error import UsiError

from usi_test_data import usis_to_test


@pytest.fixture(autouse=True)
def clear_cache():
    parsing.parse_usi.cache_clear()


@functools.lru_cache(None)
def _get_splash_remote(spectrum):
    payload = {'ions': [{'mass': float(mz), 'intensity': float(intensity)}
                        for mz, intensity in zip(spectrum.mz,
                                                 spectrum.intensity)],
               'type': 'MS'}
    headers = {'Content-type': 'application/json; charset=UTF-8'}
    splash_response = requests.post(
        'https://splash.fiehnlab.ucdavis.edu/splash/it',
        data=json.dumps(payload), headers=headers)
    if splash_response.status_code != 200:
        pytest.skip('external SPLASH unavailable')
    return splash_response.text


def test_parse_usi():
    # ValueError will be thrown if invalid USI.
    for usi in usis_to_test:
        spectrum, _, splash_key = parsing.parse_usi(usi)
        assert splash_key == _get_splash_remote(spectrum)
        if any(collection in usi for collection in
               ['MASSIVEKB', 'GNPS', 'MASSBANK', 'MS2LDA', 'MOTIFDB']):
            spectrum, _, splash_key = parsing.parse_usi(
                usi.replace('mzspec', 'mzdraft'))
            assert splash_key == _get_splash_remote(spectrum)


def test_parse_usi_invalid():
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi('this:is:an:invalid:usi')
    assert exc_info.value.error_code == 400
    # Invalid preamble.
    # FIXME: Exception not thrown because of legacy parsing.
    # with pytest.raises(UsiError) as exc_info:
    #     parsing.parse_usi('not_mzspec:PXD000561:'
    #                       'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    # assert exc_info.value.error_code == 400
    # Invalid collection.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi('mzspec:PXD000000000:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    assert exc_info.value.error_code == 400
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi('mzspec:RANDOM666:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555')
    assert exc_info.value.error_code == 400
    # Invalid index.
    # FIXME: Exception not thrown because of legacy parsing.
    # with pytest.raises(UsiError) as exc_info:
    #     parsing.parse_usi('mzspec:PXD000561:'
    #                       'Adult_Frontalcortex_bRP_Elite_85_f09:'
    #                       'not_scan:17555')
    # assert exc_info.value.error_code == 400
    # Missing index.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi('mzspec:PXD000561:'
                          'Adult_Frontalcortex_bRP_Elite_85_f09:scan:')
    assert exc_info.value.error_code == 400


def test_parse_gnps_task():
    usi = ('mzspec:GNPS:TASK-c95481f0c53d42e78a61bf899e9f9adb-spectra/'
           'specs_ms.mgf:scan:1943')
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid task pattern.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':TASK-', ':TASK-666'))
    assert exc_info.value.error_code == 400
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':scan:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid file name.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace('specs_ms.mgf', 'nonexisting.mgf'))
    assert exc_info.value.error_code == 404
    # Invalid scan number.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':1943', ':this_scan_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_gnps_library():
    usi = 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077'
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid accession.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':CCMSLIB00005436077',
                                      ':this_accession_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_massbank():
    usi = 'mzspec:MASSBANK::accession:SM858102'
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid accession.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':SM858102',
                                      ':this_accession_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_ms2lda():
    usi = 'mzspec:MS2LDA:TASK-190:accession:270684'
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid task pattern.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':TASK-', ':TASK-bla'))
    assert exc_info.value.error_code == 400
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid experiment ID.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':TASK-190', ':TASK-666666666'))
    assert exc_info.value.error_code == 404
    # Invalid document ID.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':270684',
                                      ':this_document_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_msv_pxd():
    usi = 'mzspec:MSV000079514:Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555'
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid collection.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':MSV000079514:', ':MSV666666666:'))
    assert exc_info.value.error_code == 404
    # Invalid file name.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace('Adult_Frontalcortex_bRP_Elite_85_f09',
                                      'this_filename_does_not_exist'))
    assert exc_info.value.error_code == 404
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':scan:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid scan number.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':17555', ':this_scan_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_motifdb():
    usi = 'mzspec:MOTIFDB::accession:171163'
    spectrum, _, splash_key = parsing.parse_usi(usi)
    assert splash_key == _get_splash_remote(spectrum)
    # Invalid index flag.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':accession:', ':index:'))
    assert exc_info.value.error_code == 400
    # Invalid index.
    with pytest.raises(UsiError) as exc_info:
        parsing.parse_usi(usi.replace(':171163', ':this_index_does_not_exist'))
    assert exc_info.value.error_code == 404


def test_parse_timeout():
    with unittest.mock.patch(
            'parsing.requests.get',
            side_effect=UsiError('Timeout while retrieving the USI from an '
                                 'external resource', 504)) as _:
        with pytest.raises(UsiError) as exc_info:
            usi = 'mzspec:MASSBANK::accession:SM858102'
            parsing.parse_usi(usi)
        assert exc_info.value.error_code == 504


def _get_plotting_args(**kwargs):
    plotting_args = views.default_plotting_args.copy()
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


def test_get_plotting_args_unspecified_mz_range():
    plotting_args = views._get_plotting_args(_get_plotting_args())
    assert plotting_args['mz_min'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args())
    assert plotting_args['mz_max'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args(), mirror=True)
    assert plotting_args['mz_min'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args(), mirror=True)
    assert plotting_args['mz_max'] is None


def test_get_plotting_args_invalid_mz_range():
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_min=-100))
    assert plotting_args['mz_min'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_max=-100))
    assert plotting_args['mz_max'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_min=-100),
                                             mirror=True)
    assert plotting_args['mz_min'] is None
    plotting_args = views._get_plotting_args(_get_plotting_args(mz_max=-100),
                                             mirror=True)
    assert plotting_args['mz_max'] is None


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
    plotting_args = views._get_plotting_args(_get_plotting_args(
        annotate_precision=-1), mirror=True)
    assert (plotting_args['annotate_precision']
            == views.default_plotting_args['annotate_precision'])


def test_get_plotting_args_invalid_fragment_mz_tolerance():
    plotting_args = views._get_plotting_args(_get_plotting_args(
        fragment_mz_tolerance=-1))
    assert (plotting_args['fragment_mz_tolerance']
            == views.default_plotting_args['fragment_mz_tolerance'])
    plotting_args = views._get_plotting_args(_get_plotting_args(
        fragment_mz_tolerance=-1), mirror=True)
    assert (plotting_args['fragment_mz_tolerance']
            == views.default_plotting_args['fragment_mz_tolerance'])


def test_get_plotting_args_title():
    usi = 'mzspec:MOTIFDB::accession:171163'
    plot_title = 'Custom title'
    plotting_args = views._get_plotting_args(_get_plotting_args(
        usi=usi))
    assert plotting_args['plot_title'] == usi
    plotting_args = views._get_plotting_args(_get_plotting_args(
        usi=usi, plot_title=plot_title))
    assert plotting_args['plot_title'] == plot_title


def test_prepare_spectrum():
    usi = 'mzspec:MOTIFDB::accession:171163'
    spectrum, _, _ = parsing.parse_usi(usi)
    spectrum_processed = views._prepare_spectrum(
        spectrum, **views._get_plotting_args(_get_plotting_args(
            mz_min=400, mz_max=700, annotate_peaks=json.dumps([[]]))))
    assert spectrum is not spectrum_processed
    assert len(spectrum.mz) == 49
    assert len(spectrum_processed.mz) == 5
    assert spectrum_processed.intensity.max() == 1
    assert len(spectrum_processed.mz) == len(spectrum_processed.annotation)
    assert all([annotation is None
                for annotation in spectrum_processed.annotation])


def test_prepare_spectrum_annotate_peaks_default():
    usi = 'mzspec:MOTIFDB::accession:171163'
    spectrum, _, _ = parsing.parse_usi(usi)
    spectrum_processed = views._prepare_spectrum(
        spectrum, **views._get_plotting_args(_get_plotting_args()))
    assert not all([annotation is None
                    for annotation in spectrum_processed.annotation])


def test_prepare_spectrum_annotate_peaks_specified():
    usi = 'mzspec:MOTIFDB::accession:171163'
    spectrum, _, _ = parsing.parse_usi(usi)
    spectrum_processed = views._prepare_spectrum(
        spectrum, **views._get_plotting_args(_get_plotting_args(
            mz_min=400, mz_max=700,
            annotate_peaks=json.dumps([[477.2525, 654.3575]]))))
    assert sum([annotation is not None
                for annotation in spectrum_processed.annotation]) == 2
    assert spectrum_processed.annotation[0] is None
    assert spectrum_processed.annotation[1] is not None
    assert spectrum_processed.annotation[2] is None
    assert spectrum_processed.annotation[3] is None
    assert spectrum_processed.annotation[4] is not None


def test_prepare_spectrum_annotate_peaks_specified_invalid():
    usi = 'mzspec:MOTIFDB::accession:171163'
    spectrum, _, _ = parsing.parse_usi(usi)
    spectrum_processed = views._prepare_spectrum(
        spectrum, **views._get_plotting_args(_get_plotting_args(
            annotate_peaks=json.dumps([[1477.2525, 1654.3575]]))))
    assert all([annotation is None
                for annotation in spectrum_processed.annotation])


def test_prepare_mirror_spectra():
    usi1 = 'mzspec:MOTIFDB::accession:171163'
    usi2 = 'mzspec:MOTIFDB::accession:171164'
    spectrum1, _, _ = parsing.parse_usi(usi1)
    spectrum2, _, _ = parsing.parse_usi(usi2)
    spectrum1_processed, spectrum2_processed = views._prepare_mirror_spectra(
        spectrum1, spectrum2, views._get_plotting_args(_get_plotting_args(
            mz_min=400, mz_max=700, annotate_peaks=json.dumps([[], []])),
            mirror=True))
    assert spectrum1 is not spectrum1_processed
    assert spectrum2 is not spectrum2_processed
    assert len(spectrum1.mz) == 49
    assert len(spectrum2.mz) == 28
    assert len(spectrum1_processed.mz) == 5
    assert len(spectrum2_processed.mz) == 9
    assert spectrum1_processed.intensity.max() == 1
    assert spectrum2_processed.intensity.max() == 1
    assert len(spectrum1_processed.mz) == len(spectrum1_processed.annotation)
    assert len(spectrum2_processed.mz) == len(spectrum2_processed.annotation)
    assert all([annotation is None
                for annotation in spectrum1_processed.annotation])
    assert all([annotation is None
                for annotation in spectrum2_processed.annotation])


def test_cosine():
    intensity = [1, 2, 3, 4, 5]
    intensity = intensity / np.linalg.norm(intensity)
    spectrum1 = sus.MsmsSpectrum(
        '1', 200, 1, [100, 110, 120, 130, 140], intensity)
    spectrum2 = sus.MsmsSpectrum(
        '2', 240, 1, [100, 110, 120, 155, 170], intensity)
    spectrum3 = sus.MsmsSpectrum(
        '3', 240, 1, [100, 110, 119.9, 120, 200], intensity)
    # Standard cosine.
    cosine, peak_matches = views._cosine(spectrum1, spectrum2, 0.02, False)
    assert cosine == pytest.approx(intensity[0] * intensity[0] +
                                   intensity[1] * intensity[1] +
                                   intensity[2] * intensity[2])
    assert peak_matches == [(2, 2), (1, 1), (0, 0)]
    # Shifted cosine.
    cosine, peak_matches = views._cosine(spectrum1, spectrum2, 0.02, True)
    assert cosine == pytest.approx(intensity[0] * intensity[0] +
                                   intensity[1] * intensity[1] +
                                   intensity[2] * intensity[2] +
                                   intensity[3] * intensity[4])
    assert peak_matches == [(3, 4), (2, 2), (1, 1), (0, 0)]
    # Greedy peak matching.
    cosine, peak_matches = views._cosine(spectrum1, spectrum3, 0.02, False)
    assert cosine == pytest.approx(intensity[0] * intensity[0] +
                                   intensity[1] * intensity[1] +
                                   intensity[2] * intensity[3])
    assert peak_matches == [(2, 3), (1, 1), (0, 0)]
