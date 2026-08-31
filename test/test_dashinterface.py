from unittest import mock

import requests


USI_1 = "mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005436077"
USI_2 = "mzspec:MASSBANK::accession:EA266604"


def test_process_usi_does_not_make_loopback_request():
    from metabolomics_spectrum_resolver import dashinterface

    drawing_controls = {"usi1": USI_1}
    with mock.patch.object(
        dashinterface.tasks,
        "parse_usi",
        return_value=(None, "https://example.org/source", "splash"),
    ), mock.patch.object(
        requests,
        "get",
        side_effect=AssertionError("Dash rendering must not make HTTP requests"),
    ) as request_get:
        _, image = dashinterface._process_usi(USI_1, drawing_controls)

    request_get.assert_not_called()
    assert image.src == (
        "/svg/?usi1="
        "mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005436077"
    )


def test_process_mirror_usi_does_not_make_loopback_request():
    from metabolomics_spectrum_resolver import dashinterface

    drawing_controls = {"usi1": USI_1, "usi2": USI_2}
    with mock.patch.object(
        dashinterface.tasks,
        "parse_usi",
        return_value=(None, "https://example.org/source", "splash"),
    ) as parse_usi, mock.patch.object(
        requests,
        "get",
        side_effect=AssertionError("Dash rendering must not make HTTP requests"),
    ) as request_get:
        _, image, _ = dashinterface._process_mirror_usi(
            USI_1, USI_2, drawing_controls
        )

    request_get.assert_not_called()
    assert parse_usi.call_count == 2
    assert image.src == (
        "/svg/mirror/?usi1="
        "mzspec%3AGNPS%3AGNPS-LIBRARY%3Aaccession%3ACCMSLIB00005436077"
        "&usi2=mzspec%3AMASSBANK%3A%3Aaccession%3AEA266604"
    )
