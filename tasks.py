import io
import sys
from typing import Any, Tuple

import celery
import celery_once
import joblib
import spectrum_utils.spectrum as sus

import parsing
import drawing


memory = joblib.Memory('temp/joblibcache', verbose=0)
cached_parse_usi = memory.cache(parsing.parse_usi)
cached_generate_figure = memory.cache(drawing.generate_figure)
cached_generate_mirror_figure = memory.cache(drawing.generate_mirror_figure)

celery_instance = celery.Celery(
    'tasks',
    backend='redis://metabolomicsusi-redis',
    broker='pyamqp://guest@metabolomicsusi-rabbitmq//'
)

celery_instance.conf.update(
    task_serializer='pickle',
    result_serializer='pickle',
    accept_content=['pickle', 'json']
)

celery_instance.conf.ONCE = {
    'backend': 'celery_once.backends.Redis',
    'settings': {
        'url': 'redis://metabolomicsusi-redis:6379/0',
        'default_timeout': 60,
        'blocking': True,
        'blocking_timeout': 60
    }
}

celery_instance.conf.task_routes = {
    'tasks.task_compute_heartbeat': {'queue': 'worker'},
    'tasks.task_parse_usi': {'queue': 'worker'},
    'tasks.task_generate_figure': {'queue': 'worker'},
    'tasks.task_generate_mirror_figure': {'queue': 'worker'},
}


@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def task_parse_usi(usi: str) -> Tuple[sus.MsmsSpectrum, str, str]:
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
        A tuple of the `MsmsSpectrum`, its source link, and its SPLASH.
    """
    return cached_parse_usi(usi)


@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def task_generate_figure(spectrum: sus.MsmsSpectrum, extension: str,
                         **kwargs: Any) -> io.BytesIO:
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


@celery_instance.task(time_limit=60, base=celery_once.QueueOnce)
def task_generate_mirror_figure(spectrum_top: sus.MsmsSpectrum,
                                spectrum_bottom: sus.MsmsSpectrum,
                                extension: str, **kwargs: Any) -> io.BytesIO:
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
        spectrum_top, spectrum_bottom, extension, **kwargs)


@celery_instance.task(time_limit=60)
def task_compute_heartbeat() -> str:
    """
    Return a heartbeat signal on sterr.

    Returns
    -------
    str
        Heartbeat string 'Up'.
    """
    print('Up', file=sys.stderr, flush=True)
    return 'Up'
