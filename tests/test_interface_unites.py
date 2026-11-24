"""Lecture et écriture des longueurs en pieds et pouces (interface_unites.py, PR #99)."""

import pytest

from interface_unites import ecrire_pieds_pouces, lire_pieds_pouces


@pytest.mark.parametrize(
    ("texte", "pieds"),
    [
        ("8-6", 8.5),  # 8 pi + 6 po / 12 po/pi = 8.5 pi
        ("8 - 6", 8.5),
        ("8 6", 8.5),
        ("8'-6\"", 8.5),
        ("8' 6\"", 8.5),
        ("8’ 6”", 8.5),  # apostrophes typographiques (cellulaire)
        ("8 pi 6 po", 8.5),
        ("8 pi - 6 po", 8.5),
        ("8pi6po", 8.5),
        ("8 PIEDS 6 POUCES", 8.5),
        ("8 pi - 6 1/2 po", 8 + 6.5 / 12),  # 8.5417 pi
        ("8-6 1/2", 8 + 6.5 / 12),
        ("8-6.5", 8 + 6.5 / 12),
        ("8-6,5", 8 + 6.5 / 12),  # virgule décimale acceptée à l'entrée
        ("0-3/4", 0.75 / 12),
        ("8.5", 8.5),  # pieds seulement
        ("8", 8.0),
        ("8 pi", 8.0),
        ("8'", 8.0),
        ("6 po", 0.5),  # pouces seulement : unité obligatoire
        ("6\"", 0.5),
        ("6 1/2 po", 6.5 / 12),
        ("3/4 po", 0.75 / 12),
        ("0-18", 1.5),  # 18 po = 1.5 pi
        # Fractions de pouce avec trait d'union (demande de l'utilisateur) :
        # 3 pi 2-1/4 po = 36 po + 2.25 po = 38.25 po = 3.1875 pi (971.55 mm)
        ("3 pi 2-1/4 po", 38.25 / 12),
        ("3 pi - 2-1/4 po", 38.25 / 12),
        ("3' 2-1/4\"", 38.25 / 12),
        ("3'-2-1/4\"", 38.25 / 12),
        ("3-2-1/4", 38.25 / 12),
        ("3 2 - 1/4", 38.25 / 12),
        ("2-1/4 po", 2.25 / 12),  # pouces seulement (unité obligatoire)
        ("2-1/4\"", 2.25 / 12),
        ("3-1/4", 3 + 0.25 / 12),  # sans unité : 3 pi 1/4 po
        ("3-1/4 po", 3.25 / 12),  # avec l'unité : 3 1/4 po
    ],
)
def test_lire_pieds_pouces(texte, pieds):
    assert lire_pieds_pouces(texte) == pytest.approx(pieds)


@pytest.mark.parametrize(
    "texte", ["", "   ", "huit", "8-", "-6", "8 pi po", "8/0 po", "8-6-2", "8 m", "3-2-1/", "2-/4 po"]
)
def test_lire_pieds_pouces_illisible(texte):
    with pytest.raises(ValueError):
        lire_pieds_pouces(texte)


@pytest.mark.parametrize(
    ("mm", "texte"),
    [
        (2590.8, "8 pi - 6 po"),  # 8.5 pi x 304.8 mm/pi
        (2603.5, "8 pi - 6-1/2 po"),
        (971.55, "3 pi - 2-1/4 po"),  # 38.25 po x 25.4 mm/po (exemple de l'utilisateur)  # 2603.5 mm / 25.4 mm/po = 102.5 po
        (3048.0, "10 pi - 0 po"),
        (19.05, "0 pi - 3/4 po"),  # 0.75 po
        (1295.4, "4 pi - 3 po"),
        (3000.0, "9 pi - 10-1/8 po"),  # 118.11 po -> 118 2/16 po (au 1/16 po près)
        (304.0, "0 pi - 11-15/16 po"),  # 11.9685 po x 16 = 191.5 -> 191/16 po
        (304.5, "1 pi - 0 po"),  # 11.988 po x 16 = 191.8 -> 192/16 po = 12 po = 1 pi
    ],
)
def test_ecrire_pieds_pouces(mm, texte):
    assert ecrire_pieds_pouces(mm) == texte


@pytest.mark.parametrize("mm", [2590.8, 2603.5, 971.55, 19.05, 1295.4, 6096.0])
def test_aller_retour_pieds_pouces(mm):
    # Valeurs au 1/16 po près : l'aller-retour est exact
    assert lire_pieds_pouces(ecrire_pieds_pouces(mm)) * 304.8 == pytest.approx(mm)


def test_exemple_de_l_utilisateur():
    """3 pi 2-1/4 po = 38.25 po = 38.25 po x 25.4 mm/po = 971.55 mm."""
    assert lire_pieds_pouces("3 pi 2-1/4 po") * 304.8 == pytest.approx(971.55)
