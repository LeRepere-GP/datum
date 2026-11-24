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


# --- Saisie des valeurs : calculatrice avec unités (lire_grandeur, PR #99) ---
# Valeurs attendues calculées à la main : 1 po = 25.4 mm ; 1 pi = 304.8 mm ; 1 lb = 4.4482216152605 N.

from moteur.commun.unites import ecrire_pieds_pouces, ecrire_pouces, lire_grandeur  # noqa: E402

LB = 4.4482216152605  # N


@pytest.mark.parametrize(
    ("texte", "nom", "attendu"),
    [
        # Unités seules
        ("89 mm", "dimension", 89.0),
        ("8.9 cm", "dimension", 89.0),
        ("2.4764 m", "longueur", 2476.4),
        ("3.5 po", "dimension", 88.9),
        ("3.5 in", "dimension", 88.9),
        ('3.5"', "dimension", 88.9),
        ("8 pi", "longueur", 2438.4),
        ("8'", "longueur", 2438.4),
        ("8 ft", "longueur", 2438.4),
        ("8 pieds", "longueur", 2438.4),
        # Pieds, pouces et fractions (sans tiret : « - » est une soustraction)
        ("8' 6\"", "longueur", 2590.8),  # 102 po
        ("8’ 6”", "longueur", 2590.8),  # apostrophes typographiques (cellulaire)
        ("8 pi 6 po", "longueur", 2590.8),
        ("8pi6po", "longueur", 2590.8),
        ("8 pi 6", "longueur", 2590.8),  # nombre après les pieds : des pouces
        ("8 ft 6 in", "longueur", 2590.8),
        ("3 pi 2 1/4 po", "longueur", 971.55),  # 38.25 po (exemple de l'utilisateur)
        ("1/2 po", "dimension", 12.7),
        ("2 1/4\"", "dimension", 57.15),  # 2.25 po
        ("3/4 po", "dimension", 19.05),
        # Valeurs juxtaposées additionnées
        ("8 pi 38 mm", "longueur", 2476.4),  # 2438.4 mm + 38 mm (exemple de l'utilisateur)
        ("1 m 50 mm", "longueur", 1050.0),
        # Forces et moments
        ("5 kN", "force", 5.0),
        ("5000 N", "force", 5.0),
        ("5 000 N", "force", 5.0),  # espace de milliers
        ("1124 lb", "force", 1124 * LB / 1000),
        ("1 kip", "force", LB),
        ("4.5 kN·m", "moment", 4.5),
        ("4.5 kN-m", "moment", 4.5),
        ("4.5 kNm", "moment", 4.5),
        ("4.5 kN*m", "moment", 4.5),
        ("4500 N·m", "moment", 4.5),
        ("4 500 000 N·mm", "moment", 4.5),
        ("40 000 lb·po", "moment", 40000 * LB * 25.4 / 1e6),  # 4.519 kN·m
        ("40000 lb-in", "moment", 40000 * LB * 25.4 / 1e6),
        ("10 kip-ft", "moment", 10 * LB * 304.8 / 1e3),  # 13.558 kN·m
        ("3000 lb·pi", "moment", 3000 * LB * 304.8 / 1e6),
    ],
)
def test_unites(texte, nom, attendu):
    # Avec une unité, l'unité par défaut ne change rien
    assert lire_grandeur(texte, nom, False) == pytest.approx(attendu)
    assert lire_grandeur(texte, nom, True) == pytest.approx(attendu)


@pytest.mark.parametrize(
    ("texte", "nom", "attendu"),
    [
        # Exemples de l'utilisateur
        ("8 pieds + 36 po - 50 mm", "longueur", 3302.8),  # 2438.4 mm + 914.4 mm - 50 mm
        ("(2+3)/2 po", "dimension", 63.5),  # 2.5 po : unité finale pour tout le résultat
        ("2 + 3 po", "dimension", 127.0),  # 5 po
        # Additions et soustractions (« - » est toujours une soustraction)
        ("8-6", "longueur", 2.0),  # 8 mm - 6 mm, unité par défaut métrique
        ("10 po - 2 po", "dimension", 203.2),  # 8 po
        ("2-1/4 po", "dimension", 44.45),  # 2 - 1/4 = 1.75 po
        ("8 pi - 6 po", "longueur", 2286.0),  # 7 pi 6 po = 90 po
        ("1 + 2 + 3 po", "dimension", 152.4),  # 6 po
        ("2 + 3 po + 10 mm", "dimension", 137.0),  # 5 po + 10 mm
        ("10 mm + 2", "dimension", 12.0),  # le nombre reprend l'unité voisine
        ("1500 lb + 2 kN", "force", 1.5 * LB + 2),  # 8.672 kN
        ("-2 + 5 po", "dimension", 76.2),  # 3 po
        # Multiplications et divisions
        ("3*4 kN", "force", 12.0),
        ("2 × 3 po", "dimension", 152.4),
        ("2 po x 3", "dimension", 152.4),
        ("6 ÷ 2 po", "dimension", 76.2),  # 3 po
        ("(2 po + 3 po)/2", "dimension", 63.5),
        ("8 pi 6 po / 2", "longueur", 1295.4),  # 4 pi 3 po
        ("12/6/2 mm", "dimension", 1.0),  # (12/6)/2, de gauche à droite
        ("(4)/6/2 mm", "dimension", 4 / 12),
        ("2 po / 1 po * 3 mm", "dimension", 6.0),  # rapport sans unité
        # Puissances, pourcentages, crochets
        ("2^3 mm", "dimension", 8.0),
        ("5 kN * 115%", "force", 5.75),
        ("[2+3]*2 mm", "dimension", 10.0),
        ("((1 + 1) * (2 + 3)) po", "dimension", 254.0),  # 10 po
    ],
)
def test_calculatrice(texte, nom, attendu):
    assert lire_grandeur(texte, nom) == pytest.approx(attendu)


@pytest.mark.parametrize(
    ("texte", "nom", "metrique", "imperial"),
    [
        # Résultat sans unité : unité par défaut (mm, kN, kN·m ou po, pi, lb, lb·po)
        ("89", "dimension", 89.0, 89 * 25.4),
        ("(2+3)/2", "dimension", 2.5, 63.5),  # exemple de l'utilisateur
        ("3 1/2", "dimension", 3.5, 88.9),
        ("1 000", "dimension", 1000.0, 25400.0),  # espace de milliers
        ("8.5", "longueur", 8.5, 2590.8),  # 8.5 pi en impérial
        ("8-6", "longueur", 2.0, 609.6),  # soustraction : 2 pi en impérial
        ("5", "force", 5.0, 5 * LB / 1000),
        ("40 000", "moment", 40000.0, 40000 * LB * 25.4 / 1e6),
        ("2 + 3", "dimension", 5.0, 127.0),
    ],
)
def test_unite_par_defaut(texte, nom, metrique, imperial):
    assert lire_grandeur(texte, nom, False) == pytest.approx(metrique)
    assert lire_grandeur(texte, nom, True) == pytest.approx(imperial)


@pytest.mark.parametrize(
    ("texte", "nom"),
    [
        ("", "dimension"), ("   ", "dimension"), ("trois", "dimension"), ("huit pieds", "longueur"),
        ("5 kN", "dimension"),  # unité d'une autre grandeur
        ("89 mm", "force"), ("4.5 kN", "moment"), ("5 kN·m", "force"), ("5 kg", "force"),
        ("3 po + 2 kN", "dimension"),  # unités incompatibles
        ("2 po * 3 po", "dimension"),  # une aire, pas une longueur
        ("2 +", "dimension"), ("+", "dimension"), ("(2+3", "dimension"), ("2+3)", "dimension"),
        ("1/0", "dimension"), ("10 mm / 0", "dimension"), ("2 * * 3", "dimension"),
        ("2^0.5 po", "dimension"),  # exposant entier seulement
        ("import os", "dimension"), ("__import__('os')", "dimension"),  # aucun eval()
        ("4.5 kN·m", "contrainte"),  # grandeur non offerte
    ],
)
def test_illisible(texte, nom):
    with pytest.raises(ValueError):
        lire_grandeur(texte, nom)


@pytest.mark.parametrize(
    ("mm", "texte"),
    [
        (88.9, "3 1/2"),  # 3.5 po x 25.4 mm/po
        (38.0, "1 1/2"),  # 1.496 po x 16 = 23.9 -> 24/16 po
        (89.0, "3 1/2"),  # 3.504 po x 16 = 56.06 -> 56/16 po
        (19.05, "3/4"),
        (76.2, "3"),
        (35.0, "1 3/8"),  # 1.378 po x 16 = 22.05 -> 22/16 po
    ],
)
def test_ecrire_pouces(mm, texte):
    assert ecrire_pouces(mm) == texte


@pytest.mark.parametrize(
    ("mm", "texte"),
    [
        (2590.8, "8 pi 6 po"),  # 8.5 pi x 304.8 mm/pi
        (2603.5, "8 pi 6 1/2 po"),  # 102.5 po
        (971.55, "3 pi 2 1/4 po"),  # 38.25 po (exemple de l'utilisateur)
        (3048.0, "10 pi 0 po"),
        (19.05, "0 pi 3/4 po"),
        (1295.4, "4 pi 3 po"),
        (3000.0, "9 pi 10 1/8 po"),  # 118.11 po -> 118 2/16 po (au 1/16 po près)
        (304.0, "0 pi 11 15/16 po"),  # 11.9685 po x 16 = 191.5 -> 191/16 po
        (304.5, "1 pi 0 po"),  # 11.988 po x 16 = 191.8 -> 192/16 po = 12 po = 1 pi
    ],
)
def test_ecrire_pieds_pouces(mm, texte):
    assert ecrire_pieds_pouces(mm) == texte


@pytest.mark.parametrize("mm", [2590.8, 2603.5, 971.55, 19.05, 1295.4, 6096.0, 88.9])
def test_aller_retour(mm):
    # Le texte écrit (au 1/16 po près) se relit exactement, en longueur (pi-po) et en dimension (po)
    assert lire_grandeur(ecrire_pieds_pouces(mm), "longueur") == pytest.approx(mm)
    assert lire_grandeur(ecrire_pouces(mm) + " po", "dimension") == pytest.approx(mm)
    assert lire_grandeur(ecrire_pouces(mm), "dimension", True) == pytest.approx(mm)


@pytest.mark.parametrize(
    ("virgule", "point", "nom"),
    [
        # Décimales avec un point ou une virgule : même valeur (demande de l'utilisateur)
        ("3,5 po", "3.5 po", "dimension"),  # 88.9 mm
        ("2,4764 m", "2.4764 m", "longueur"),  # 2476.4 mm
        ("8 pi 6,5 po", "8 pi 6.5 po", "longueur"),  # 102.5 po = 2603.5 mm
        ("(2,5+3,5)/2 po", "(2.5+3.5)/2 po", "dimension"),  # 3 po = 76.2 mm
        ("1,5 kip", "1.5 kip", "force"),  # 6.672 kN
        ("4,5 kN·m", "4.5 kN·m", "moment"),
        ("5 kN * 112,5%", "5 kN * 112.5%", "force"),  # 5.625 kN
        ("40 000,5 N", "40 000.5 N", "force"),  # espace de milliers et virgule décimale
        ("0,75", "0.75", "dimension"),
    ],
)
def test_point_ou_virgule_decimale(virgule, point, nom):
    assert lire_grandeur(virgule, nom) == pytest.approx(lire_grandeur(point, nom))
    assert lire_grandeur(virgule, nom, True) == pytest.approx(lire_grandeur(point, nom, True))


def test_virgule_toujours_decimale():
    """
    Décision de l'utilisateur (PR #99) : la virgule est toujours décimale, même suivie de 3 chiffres.
    « 1,500 kN » = 1.5 kN ; « 40,000 lb » = 40 lb x 4.4482 N/lb = 177.9 N = 0.1779 kN. Les milliers
    s'écrivent avec une espace (« 40 000 lb ») ou sans séparateur (« 40000 lb »).
    """
    assert lire_grandeur("1,500 kN", "force") == pytest.approx(1.5)
    assert lire_grandeur("40,000 lb", "force") == pytest.approx(40 * LB / 1000)
    assert lire_grandeur("40 000 lb", "force") == pytest.approx(40000 * LB / 1000)


@pytest.mark.parametrize(
    ("texte", "nom", "attendu"),
    [
        # « de » (ou « of ») après un pourcentage veut dire « fois » (demande de l'utilisateur)
        ("50% de 4 mm", "dimension", 2.0),
        ("50 % de 4 po", "dimension", 50.8),  # 2 po
        ("115% de 5 kN", "force", 5.75),
        ("50% of 8 pi", "longueur", 1219.2),  # 4 pi
        ("50% de (2+2) po", "dimension", 50.8),
        ("25% de 50% de 16 po", "dimension", 50.8),  # 0.25 x 0.5 x 16 po = 2 po
        ("50% de 4 + 1 po", "dimension", 76.2),  # 2 + 1 = 3 po
    ],
)
def test_pourcentage_de(texte, nom, attendu):
    assert lire_grandeur(texte, nom) == pytest.approx(attendu)


def test_pourcentage_de_sans_unite():
    """Exemple de l'utilisateur : « 50% de 4 » = 2, dans l'unité par défaut."""
    assert lire_grandeur("50% de 4", "dimension") == pytest.approx(2.0)  # 2 mm
    assert lire_grandeur("50% de 4", "dimension", True) == pytest.approx(50.8)  # 2 po


@pytest.mark.parametrize("texte", ["2 de 4", "50% de", "de 4", "50% dé 4"])
def test_de_seulement_apres_un_pourcentage(texte):
    with pytest.raises(ValueError):
        lire_grandeur(texte, "dimension")
