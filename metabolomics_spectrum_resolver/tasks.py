import io
import sys
from typing import Any, Tuple

import celery
import celery_once
import joblib
import redis
import spectrum_utils.spectrum as sus

from metabolomics_spectrum_resolver import drawing, parsing


memory = joblib.Memory("tmp/joblibcache", verbose=0)
cached_parse_usi = memory.cache(parsing.parse_usi)
cached_parse_usi_or_spectrum = memory.cache(parsing.parse_usi_or_spectrum)
cached_generate_figure = memory.cache(drawing.generate_figure)
cached_generate_mirror_figure = memory.cache(drawing.generate_mirror_figure)

celery_instance = celery.Celery(
    "tasks",
    backend="redis://metabolomicsusi-redis",
    broker="redis://metabolomicsusi-redis",
)

celery_instance.conf.update(
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle", "json"],
)

celery_instance.conf.ONCE = {
    "backend": "celery_once.backends.Redis",
    "settings": {
        "url": "redis://metabolomicsusi-redis:6379/0",
        "default_timeout": 60,
        "blocking": True,
        "blocking_timeout": 60,
    },
}

celery_instance.conf.task_routes = {
    "metabolomics_spectrum_resolver.tasks.task_compute_heartbeat": {
        "queue": "worker"
    },
    "metabolomics_spectrum_resolver.tasks._task_parse_usi": {
        "queue": "worker"
    },
    "metabolomics_spectrum_resolver.tasks._task_parse_usi_or_spectrum": {
        "queue": "worker"
    },
    "metabolomics_spectrum_resolver.tasks._task_generate_figure": {
        "queue": "worker"
    },
    "metabolomics_spectrum_resolver.tasks._task_generate_mirror_figure": {
        "queue": "worker"
    },
}

def parse_usi_or_spectrum(usi: str, spectrum: dict) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    The first attempt to parse the USI is via a Celery task. Alternatively, as
    a fallback option the USI can be parsed directly in this thread.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of (i) the `MsmsSpectrum`, (ii) its source link, and (iii) its
        SPLASH.
    """
    # First attempt to schedule with Celery.
    try:
        return _task_parse_usi_or_spectrum.apply_async(args=(usi,spectrum)).get()
    except redis.exceptions.ConnectionError:
        # Fallback in case scheduling via Celery fails.
        # Mostly used for testing.
        # noinspection PyTypeChecker
        return parsing.parse_usi_or_spectrum(usi,spectrum)

def parse_usi(usi: str) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    The first attempt to parse the USI is via a Celery task. Alternatively, as
    a fallback option the USI can be parsed directly in this thread.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of (i) the `MsmsSpectrum`, (ii) its source link, and (iii) its
        SPLASH.
    """
    # First attempt to schedule with Celery.
    try:
        return _task_parse_usi.apply_async(args=(usi,)).get()
    except redis.exceptions.ConnectionError:
        # Fallback in case scheduling via Celery fails.
        # Mostly used for testing.
        # noinspection PyTypeChecker
        return parsing.parse_usi(usi)

@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def _task_parse_usi_or_spectrum(usi: str, spectrum: dict) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    Previously computed results will be retrieved from the cache.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of (i) the `MsmsSpectrum`, (ii) its source link, and (iii) its
        SPLASH.
    """
    # noinspection PyTypeChecker
    return cached_parse_usi_or_spectrum(usi,spectrum)

@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def _task_parse_usi(usi: str) -> Tuple[sus.MsmsSpectrum, str, str]:
    """
    Retrieve the spectrum associated with the given USI.

    Previously computed results will be retrieved from the cache.

    Parameters
    ----------
    usi : str
        The USI of the spectrum to be retrieved from its resource.

    Returns
    -------
    Tuple[sus.MsmsSpectrum, str, str]
        A tuple of (i) the `MsmsSpectrum`, (ii) its source link, and (iii) its
        SPLASH.
    """
    # noinspection PyTypeChecker
    return cached_parse_usi(usi)


def generate_figure(
    spectrum: sus.MsmsSpectrum, extension: str, **kwargs: Any
) -> io.BytesIO:
    """
    Generate a spectrum plot.

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum to be plotted.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the spectrum plot.
    """
    try:
        return _task_generate_figure.apply_async(
            args=(spectrum, extension), kwargs=kwargs
        ).get()
    except redis.exceptions.ConnectionError:
        return drawing.generate_figure(spectrum, extension, **kwargs)


@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def _task_generate_figure(
    spectrum: sus.MsmsSpectrum, extension: str, **kwargs: Any
) -> io.BytesIO:
    """
    Generate a spectrum plot.

    Previously computed results will be retrieved from the cache.

    Parameters
    ----------
    spectrum : sus.MsmsSpectrum
        The spectrum to be plotted.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the spectrum plot.
    """
    return cached_generate_figure(spectrum, extension, **kwargs)


def generate_mirror_figure(
    spectrum_top: sus.MsmsSpectrum,
    spectrum_bottom: sus.MsmsSpectrum,
    extension: str,
    **kwargs: Any,
) -> io.BytesIO:
    """
    Generate a mirror plot of two spectra.

    Parameters
    ----------
    spectrum_top : sus.MsmsSpectrum
        The spectrum to be plotted at the top of the mirror plot.
    spectrum_bottom : sus.MsmsSpectrum
        The spectrum to be plotted at the bottom of the mirror plot.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the mirror plot.
    """
    try:
        return _task_generate_mirror_figure.apply_async(
            args=(spectrum_top, spectrum_bottom, extension), kwargs=kwargs
        ).get()
    except redis.exceptions.ConnectionError:
        return drawing.generate_mirror_figure(
            spectrum_top, spectrum_bottom, extension, **kwargs
        )


@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def _task_generate_mirror_figure(
    spectrum_top: sus.MsmsSpectrum,
    spectrum_bottom: sus.MsmsSpectrum,
    extension: str,
    **kwargs: Any,
) -> io.BytesIO:
    """
    Generate a mirror plot of two spectra.

    Previously computed results will be retrieved from the cache.

    Parameters
    ----------
    spectrum_top : sus.MsmsSpectrum
        The spectrum to be plotted at the top of the mirror plot.
    spectrum_bottom : sus.MsmsSpectrum
        The spectrum to be plotted at the bottom of the mirror plot.
    extension : str
        Image format.
    kwargs : Any
        Plotting settings.

    Returns
    -------
    io.BytesIO
        Bytes buffer containing the mirror plot.
    """
    return cached_generate_mirror_figure(
        spectrum_top, spectrum_bottom, extension, **kwargs
    )


@celery_instance.task(time_limit=60)
def task_compute_heartbeat() -> str:
    """
    Return a heartbeat signal on sterr.

    Returns
    -------
    str
        Heartbeat string 'Up'.
    """
    sys.stderr.write("Up")
    return "Up"
