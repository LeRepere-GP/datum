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


# --- Saisie libre en n'importe quelle unité (lire_grandeur, PR #99) ---

from moteur.commun.unites import lire_grandeur  # noqa: E402


@pytest.mark.parametrize(
    ("texte", "nom", "attendu"),
    [
        # Exemple de l'utilisateur : 8 pi x 304.8 mm/pi + 38 mm = 2438.4 mm + 38 mm = 2476.4 mm
        ("8 pi 38 mm", "longueur", 2476.4),
        ("8 pi 38 mm", "dimension", 2476.4),
        ("8' 38mm", "longueur", 2476.4),
        ("2476.4 mm", "longueur", 2476.4),
        ("2.4764 m", "longueur", 2476.4),
        ("247.64 cm", "longueur", 2476.4),
        ("89 mm", "dimension", 89.0),
        ("3-1/2 po", "dimension", 88.9),  # 3.5 po x 25.4 mm/po
        ('3 1/2"', "dimension", 88.9),
        ("3.5 in", "dimension", 88.9),
        ("3 pi 2-1/4 po", "longueur", 971.55),  # 38.25 po x 25.4 mm/po
        ("8-6", "longueur", 2590.8),  # notation des plans : 8 pi 6 po
        ("8 ft 6 in", "longueur", 2590.8),
        ("1 m 50 mm", "longueur", 1050.0),
        ("5 kN", "force", 5.0),
        ("5000 N", "force", 5.0),
        ("5 000 N", "force", 5.0),  # espace de milliers
        ("1124 lb", "force", 1124 * 4.4482216152605 / 1000),  # 4.9998 kN
        ("1 kip", "force", 4.4482216152605),
        ("5 kN + 100 lb", "force", 5 + 0.44482216152605),
        ("4.5 kN·m", "moment", 4.5),
        ("4.5 kN-m", "moment", 4.5),
        ("4.5 kNm", "moment", 4.5),
        ("4.5 kN*m", "moment", 4.5),
        ("4500 N·m", "moment", 4.5),
        ("4 500 000 N·mm", "moment", 4.5),
        ("4500 kN·mm", "moment", 4.5),
        # 40 000 lb·po x 4.4482 N/lb x 25.4 mm/po = 4 519 393 N·mm = 4.519 kN·m
        ("40 000 lb·po", "moment", 40000 * 4.4482216152605 * 25.4 / 1e6),
        ("40000 lb-in", "moment", 40000 * 4.4482216152605 * 25.4 / 1e6),
        # 10 kip·pi = 10 x 4448.2 N x 304.8 mm = 13.558 kN·m
        ("10 kip-ft", "moment", 10 * 4.4482216152605 * 304.8 / 1e3),
        ("3000 lb·pi", "moment", 3000 * 4.4482216152605 * 304.8 / 1e6),
    ],
)
def test_lire_grandeur_avec_unites(texte, nom, attendu):
    # Avec une unité, l'unité par défaut ne change rien
    assert lire_grandeur(texte, nom, False) == pytest.approx(attendu)
    assert lire_grandeur(texte, nom, True) == pytest.approx(attendu)


@pytest.mark.parametrize(
    ("texte", "nom", "metrique", "imperial"),
    [
        # Nombre sans unité : unité par défaut (mm, kN, kN·m ou po, pi-po, lb, lb·po)
        ("89", "dimension", 89.0, 89 * 25.4),
        ("3-1/2", "dimension", 3.5, 88.9),
        ("1 000", "dimension", 1000.0, 25400.0),  # espace de milliers, pas 1 pi 0 po
        ("3000", "longueur", 3000.0, 3000 * 304.8),
        ("8.5", "longueur", 8.5, 2590.8),  # 8.5 pi en impérial
        ("3-1/4", "longueur", 3.25, 920.75),  # impérial : 3 pi 1/4 po = 36.25 po
        ("5", "force", 5.0, 5 * 4.4482216152605 / 1000),
        ("40 000", "moment", 40000.0, 40000 * 4.4482216152605 * 25.4 / 1e6),
    ],
)
def test_lire_grandeur_sans_unite(texte, nom, metrique, imperial):
    assert lire_grandeur(texte, nom, False) == pytest.approx(metrique)
    assert lire_grandeur(texte, nom, True) == pytest.approx(imperial)


@pytest.mark.parametrize(
    ("texte", "nom"),
    [
        ("", "dimension"), ("trois", "dimension"), ("5 kN", "dimension"), ("89 mm", "force"),
        ("5 kg", "force"), ("4.5 kN", "moment"), ("8 pi mm", "longueur"),
        ("-5 kN", "force"), ("5 kN 3", "force"), ("4.5 kN·m", "contrainte"),
    ],
)
def test_lire_grandeur_illisible(texte, nom):
    with pytest.raises(ValueError):
        lire_grandeur(texte, nom)


@pytest.mark.parametrize(
    ("texte", "nom", "imperial", "attendu"),
    [
        # Avec « + », un nombre sans unité prend l'unité du terme suivant (exemple de l'utilisateur)
        ("2 + 3 po", "dimension", False, 127.0),  # 5 po x 25.4 mm/po
        ("2+3 po", "dimension", False, 127.0),
        ("1 + 2 + 3 po", "dimension", False, 152.4),  # 6 po
        ("2 + 3 po + 10 mm", "dimension", False, 137.0),  # 5 po + 10 mm
        ("8 pi + 38 mm", "longueur", False, 2476.4),
        ("2 + 3 kN", "force", False, 5.0),
        ("1500 lb + 2 kN", "force", False, 1500 * 4.4482216152605 / 1000 + 2),  # 8.672 kN
        # Aucune unité : l'unité par défaut
        ("2 + 3", "dimension", False, 5.0),  # 5 mm
        ("2 + 3", "dimension", True, 127.0),  # 5 po
    ],
)
def test_lire_grandeur_somme(texte, nom, imperial, attendu):
    assert lire_grandeur(texte, nom, imperial) == pytest.approx(attendu)


@pytest.mark.parametrize("texte", ["2 +", "+ 3 po", "2 + + 3 po"])
def test_lire_grandeur_somme_illisible(texte):
    with pytest.raises(ValueError):
        lire_grandeur(texte, "dimension")
