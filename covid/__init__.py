"""
Covid

Implements epidemiological simulations for the COVID-19.
"""
__version__ = "0.1.0"
__author__ = "Fábio Mendes"
import gettext as _gettext
from pathlib import Path as _Path

from .region import Region, region

LOCALEDIR = _Path(__file__).parent / "locale"


def set_i18n(code):
    _gettext.bindtextdomain(code, localedir=LOCALEDIR)


gettext = _gettext.gettext
