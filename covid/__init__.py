"""
Covid

Epidemiological calculator tuned specifically for COVID-19.
"""
__version__ = "0.1.0"
__author__ = "Fábio Mendes"
from gettext import gettext
from pathlib import Path as _Path

from . import models
from .region import Region, region

LOCALEDIR = _Path(__file__).parent / "locale"


def set_i18n(lang, language=...):
    """
    Set locale and translations.

    Examples:
        set_i18n('pt_BR.UTF-8') -> set locale to pt_BR.UTF-8 and language to pt_BR.
    """
    import gettext
    import locale
    import warnings

    if language is ...:
        language = lang.partition(".")[0]
    if language:
        gettext.bindtextdomain(language or "messages", localedir=LOCALEDIR)
    try:
        locale.setlocale(locale.LC_ALL, lang)
    except locale.Error:
        warnings.warn(f"locale is not supported: {lang}")


def _run():
    import os

    # Use environment variables to set i18n and l13n configurations.
    # LANGUAGE -> language part of the locale, e.g., pt_BR
    # LANG -> full locale string, e.g., pt_BR.UTF-8
    language = os.environ.get("LANGUAGE", "messages")
    language = os.environ.get("COVID_LANGUAGE", language)

    lang = os.environ.get("COVID_LANG") or os.environ.get("LANG")
    set_i18n(lang, language)


_run()
_ = gettext
del _run, _Path
