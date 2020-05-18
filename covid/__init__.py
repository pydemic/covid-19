"""
Covid

Epidemiological calculator tuned specifically for COVID-19.
"""
__version__ = "0.1.1"
__author__ = "Fábio Mendes"
from gettext import gettext
from pathlib import Path as _Path

from . import models
from .region import Region, region

LOCALEDIR = _Path(__file__).parent / "locale"


def set_i18n(lang, language=None):
    """
    Set locale and translations.

    Examples:
        set_i18n('pt_BR.UTF-8') -> set locale to pt_BR.UTF-8 and language to pt_BR.
    """
    import gettext
    import locale
    import warnings
    import os

    try:
        locale.setlocale(locale.LC_ALL, lang)
        locale.setlocale(locale.LC_MESSAGES, language or lang)
        os.environ["LANG"] = lang
        os.environ["LANGUAGE"] = language or lang.split(".")[0]
    except locale.Error:
        warnings.warn(f"locale is not supported: {lang}")
    gettext.bindtextdomain("messages", localedir=LOCALEDIR)


def _run():
    import os

    lang = os.environ.get("COVID_LANG") or os.environ.get("LANG")
    set_i18n(lang)


_run()
_ = gettext
del _run, _Path
