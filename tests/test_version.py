"""Version de Datum (décision de l'utilisateur : 0.1.0), dans l'application et la note PDF."""

import re

from moteur import VERSION
from moteur.commun.note_de_calcul import donnees_de_la_note
from tests.moteur.commun.test_note_de_calcul import ENTETE, flexion
from tests.test_acces import _connecte


def test_format_de_la_version():
    assert VERSION == "0.2.0"
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION)  # MAJEUR.MINEUR.CORRECTIF


def test_version_dans_la_note():
    assert donnees_de_la_note([("Solive S-1", flexion())], ENTETE)["version"] == "0.2.0"


def test_version_dans_la_barre_laterale():
    at = _connecte("admin", "mot-admin")
    assert "Datum 0.2.0" in [c.value for c in at.sidebar.caption]
