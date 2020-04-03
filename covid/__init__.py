"""
Covid

Epidemiological calculator tuned specifically for COVID-19.
"""
__version__ = "0.1.0"
__author__ = "Fábio Mendes"
from pathlib import Path as _Path

from . import models
from .region import Region, region
from gettext import gettext

LOCALEDIR = _Path(__file__).parent / "locale"


def set_i18n(code):
    import gettext

    gettext.bindtextdomain(code, localedir=LOCALEDIR)


def _run():
    import os
    import locale

    # Use environment variables to set i18n and l13n configurations.
    # LANGUAGE -> language part of the locale, e.g., pt_BR
    # LANG -> full locale string, e.g., pt_BR.UTF-8
    language = os.environ.get("LANGUAGE", "messages")
    language = os.environ.get("COVID_LANGUAGE", language)
    set_i18n(language)

    lang = os.environ.get("COVID_LANG") or os.environ.get("LANG")
    if lang:
        locale.setlocale(locale.LC_ALL, lang)


_run()
_ = gettext
del _run, _Path
