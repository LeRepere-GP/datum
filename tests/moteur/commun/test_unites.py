"""Tests de moteur/commun/unites.py : conversions pour l'affichage (valeurs calculées à la main)."""

import pytest

from moteur.commun import unites


# (valeur métrique, grandeur, valeur impériale attendue) : calculs à la main
@pytest.mark.parametrize(
    "valeur, nom, attendu",
    [
        (38, "dimension", 1.49606),  # 38 mm / 25,4 mm/po = 1,49606 po
        (3000, "longueur", 9.84252),  # 3000 mm / 304,8 mm/pi = 9,84252 pi
        (5320, "aire", 8.24602),  # 5320 mm² / 645,16 mm²/po² = 8,24602 po²
        (12.62, "force", 2837.089),  # 12 620 N / 4,448 221 6 N/lb = 2837,089 lb
        (1, "moment", 8850.746),  # 10^6 N·mm / (4,448 221 6 N/lb x 25,4 mm/po) = 8850,746 lb·po
        # 1 psi = 1 lb/po² = 4,448 221 6 N / 645,16 mm² = 0,006 894 76 MPa
        # 11,5 MPa / 0,006 894 76 MPa/psi = 1667,937 psi
        (11.5, "contrainte", 1667.937),
    ],
)
def test_vers_imperial(valeur, nom, attendu):
    assert unites.vers_imperial(valeur, nom) == pytest.approx(attendu, rel=1e-5)


@pytest.mark.parametrize("nom", sorted(unites.GRANDEURS))
def test_aller_retour(nom):
    # 123,456 (unité métrique de la grandeur) -> impérial -> métrique : même valeur
    assert unites.vers_metrique(unites.vers_imperial(123.456, nom), nom) == pytest.approx(123.456)


def test_facteurs_exacts():
    # 1 po = 25,4 mm ; 1 pi = 304,8 mm ; 1 lb = 0,004 448 221 615 260 5 kN ; 1 psi = 0,006 894 76 MPa
    assert unites.vers_metrique(1, "dimension") == 25.4
    assert unites.vers_metrique(1, "longueur") == pytest.approx(304.8)
    assert unites.vers_metrique(1, "force") == pytest.approx(0.0044482216152605)
    assert unites.vers_metrique(1, "contrainte") == pytest.approx(0.00689475729)


@pytest.mark.parametrize(
    "valeur, nom, attendu",
    [
        (38, "dimension", "38 mm (1.50 po)"),
        (3000, "longueur", "3000 mm (9.84 pi)"),
        (12.62, "force", "12.62 kN (2837 lb)"),
        (1, "moment", "1.00 kN·m (8851 lb·po)"),
        (11.5, "contrainte", "11.50 MPa (1668 psi)"),
    ],
)
def test_deux_unites(valeur, nom, attendu):
    assert unites.deux_unites(valeur, nom) == attendu


def test_grandeur_inconnue():
    with pytest.raises(KeyError):
        unites.vers_imperial(1, "vitesse")


# --- Longueurs impériales : pieds, pouces et fractions de pouce (lire_imperial, PR #99) ---

from moteur.commun.unites import ecrire_pieds_pouces, ecrire_pouces, lire_imperial  # noqa: E402


@pytest.mark.parametrize(
    ("texte", "pouces"),
    [
        # Pieds et pouces (toutes unités par défaut)
        ("8-6", 102.0),  # 8 pi x 12 po/pi + 6 po
        ("8 - 6", 102.0),
        ("8 6", 102.0),
        ("8'-6\"", 102.0),
        ("8' 6\"", 102.0),
        ("8’ 6”", 102.0),  # apostrophes typographiques (cellulaire)
        ("8 pi 6 po", 102.0),
        ("8 pi - 6 po", 102.0),
        ("8pi6po", 102.0),
        ("8 PIEDS 6 POUCES", 102.0),
        ("8-6.5", 102.5),
        ("8-6,5", 102.5),  # virgule décimale acceptée à l'entrée
        ("0-18", 18.0),
        # Fractions de pouce (exemple de l'utilisateur : 3 pi 2-1/4 po = 38.25 po = 971.55 mm)
        ("3 pi 2-1/4 po", 38.25),
        ("3 pi - 2-1/4 po", 38.25),
        ("3' 2-1/4\"", 38.25),
        ("3'-2-1/4\"", 38.25),
        ("3-2-1/4", 38.25),
        ("3 2 - 1/4", 38.25),
        ("8 pi - 6 1/2 po", 102.5),
        ("8-6 1/2", 102.5),
        # Pieds seulement, avec l'unité
        ("8 pi", 96.0),
        ("8'", 96.0),
        # Pouces seulement, avec l'unité
        ("6 po", 6.0),
        ("6\"", 6.0),
        ("2-1/4 po", 2.25),
        ("2-1/4\"", 2.25),
        ("6 1/2 po", 6.5),
        ("3/4 po", 0.75),
    ],
)
@pytest.mark.parametrize("unite_par_defaut", ["po", "pi"])
def test_lire_imperial(texte, pouces, unite_par_defaut):
    assert lire_imperial(texte, unite_par_defaut) == pytest.approx(pouces)


@pytest.mark.parametrize(
    ("texte", "unite_par_defaut", "pouces"),
    [
        # Nombre sans unité : dans l'unité par défaut du champ
        ("3.5", "po", 3.5),
        ("3-1/2", "po", 3.5),
        ("3 1/2", "po", 3.5),
        ("3/4", "po", 0.75),
        ("3", "po", 3.0),
        ("8.5", "pi", 102.0),  # 8.5 pi x 12 po/pi
        ("8", "pi", 96.0),
        # Champ en pieds : « 3-1/4 » se lit 3 pi 1/4 po (notation des plans)
        ("3-1/4", "pi", 36.25),
        ("3-1/4 po", "pi", 3.25),  # avec l'unité : 3 1/4 po
    ],
)
def test_lire_imperial_unite_par_defaut(texte, unite_par_defaut, pouces):
    assert lire_imperial(texte, unite_par_defaut) == pytest.approx(pouces)


@pytest.mark.parametrize(
    "texte", ["", "   ", "huit", "8-", "-6", "8 pi po", "8/0 po", "8-6-2", "8 m", "3-2-1/", "2-/4 po"]
)
def test_lire_imperial_illisible(texte):
    with pytest.raises(ValueError):
        lire_imperial(texte)


def test_lire_imperial_unite_par_defaut_inconnue():
    with pytest.raises(ValueError, match="Unité par défaut"):
        lire_imperial("3", "m")


def test_exemple_de_l_utilisateur():
    """3 pi 2-1/4 po = 38.25 po x 25.4 mm/po = 971.55 mm."""
    assert unites.vers_metrique(lire_imperial("3 pi 2-1/4 po"), "dimension") == pytest.approx(971.55)


@pytest.mark.parametrize(
    ("mm", "texte"),
    [
        (88.9, "3-1/2"),  # 3.5 po x 25.4 mm/po
        (38.0, "1-1/2"),  # 1.496 po x 16 = 23.9 -> 24/16 po
        (89.0, "3-1/2"),  # 3.504 po x 16 = 56.06 -> 56/16 po
        (19.05, "3/4"),
        (76.2, "3"),
        (35.0, "1-3/8"),  # 1.378 po x 16 = 22.05 -> 22/16 po
    ],
)
def test_ecrire_pouces(mm, texte):
    assert ecrire_pouces(mm) == texte


@pytest.mark.parametrize(
    ("mm", "texte"),
    [
        (2590.8, "8 pi - 6 po"),  # 8.5 pi x 304.8 mm/pi
        (2603.5, "8 pi - 6-1/2 po"),  # 102.5 po
        (971.55, "3 pi - 2-1/4 po"),  # 38.25 po (exemple de l'utilisateur)
        (3048.0, "10 pi - 0 po"),
        (19.05, "0 pi - 3/4 po"),
        (1295.4, "4 pi - 3 po"),
        (3000.0, "9 pi - 10-1/8 po"),  # 118.11 po -> 118 2/16 po (au 1/16 po près)
        (304.0, "0 pi - 11-15/16 po"),  # 11.9685 po x 16 = 191.5 -> 191/16 po
        (304.5, "1 pi - 0 po"),  # 11.988 po x 16 = 191.8 -> 192/16 po = 12 po = 1 pi
    ],
)
def test_ecrire_pieds_pouces(mm, texte):
    assert ecrire_pieds_pouces(mm) == texte


@pytest.mark.parametrize("mm", [2590.8, 2603.5, 971.55, 19.05, 1295.4, 6096.0, 88.9])
def test_aller_retour_imperial(mm):
    # Valeurs au 1/16 po près : l'aller-retour est exact, dans les deux écritures
    assert unites.vers_metrique(lire_imperial(ecrire_pieds_pouces(mm), "pi"), "dimension") == pytest.approx(mm)
    assert unites.vers_metrique(lire_imperial(ecrire_pouces(mm), "po"), "dimension") == pytest.approx(mm)
