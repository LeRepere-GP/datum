"""
Tests de moteur/commun/calculatrice.py : calculatrice d'unités (issue #100).

Valeurs attendues calculées à la main avec les facteurs exacts : 1 po = 25.4 mm ; 1 pi = 304.8 mm ;
1 lb = 4.448 221 615 260 5 N.
"""

import pytest

from moteur.commun.calculatrice import calculer

LB = 4.4482216152605  # N


# (texte, unité de sortie, valeur attendue dans cette unité)
@pytest.mark.parametrize(
    "texte, unite, attendu",
    [
        # Exemples de l'utilisateur (issue #100)
        # 8 po x 600 mm = 203.2 mm x 600 mm = 121 920 mm² = 0.12192 m²
        ('8" x 600 mm en m²', None, 0.12192),
        ('8" x 600 mm en m2?', None, 0.12192),
        # 400 lb = 1779.289 N ; 3 po x 3.25 po = 9.75 po² = 6290.31 mm² ;
        # 1779.289 N / 6290.31 mm² = 0.282 862 MPa = 282.862 kPa (vérif. : 41.026 psi x 6.894 76 kPa/psi)
        ('400 lb sur 3 po x 3 1/4" en kPa', None, 282.862),
        # 2 mm x 685.8 mm = 1371.6 mm² ; 1371.6 mm² / 92 903.04 mm²/pi² = 0.014 763 78 pi²
        ("2 mm * 27 po en pi²", None, 0.01476378),  # = 54 mm·po / (144 po²/pi² x 25.4 mm/po)
        # Analyse dimensionnelle
        ("3 pi * 4 pi", "pi²", 12.0),
        ("3 pi * 4 pi", "m²", 1.1148364),  # 914.4 mm x 1219.2 mm = 1 114 836 mm² = 1.114 836 m²
        ("5 kN * 2 m", "kN·m", 10.0),  # 5000 N x 2000 mm = 1e7 N·mm = 10 kN·m
        ("5 kN-m", "kN·m", 5.0),
        ("5 kn.m", "N·mm", 5e6),
        ("1 kip·pi", "kN·m", 1.3558179),  # 4448.22 N x 304.8 mm = 1 355 818 N·mm = 1.355 818 kN·m
        ("3 kN/m", "lb/pi", 205.5652),  # 3 N/mm x 304.8 mm/pi / 4.448 22 N/lb = 205.565 lb/pi
        ("100 psf x 12 pi", "plf", 1200.0),
        ("2.4 kPa * 3 m", "kN/m", 7.2),  # 0.0024 N/mm² x 3000 mm = 7.2 N/mm = 7.2 kN/m
        ("12 kN / (3 m * 2 m)", "kPa", 2.0),  # 12 000 N / 6e6 mm² = 0.002 MPa = 2 kPa
        ("(38 mm)^2 * 235 mm / 6", "mm³", 56556.67),  # 1444 x 235 / 6 = 339 340 / 6 = 56 556.67 mm³
        ("38 mm * (235 mm)^2 / 6", "mm³", 349758.33),  # b d² / 6 = 38 x 235² / 6 = 349 758.33 mm³
        ("38 mm x 235 mm^2", "mm³", 8930.0),  # « mm^2 » est l'unité mm² : 38 mm x 235 mm²
        ("1 m^3", "pi³", 35.314667),  # 1e9 mm³ / 28 316 846.6 mm³/pi³ = 35.314 667 pi³
        ("1 po^4", "mm⁴", 416231.43),  # 25.4⁴ = 416 231.43 mm⁴
        # Unités de pression, de charge répartie et de poids volumique
        ("1 psf", "Pa", 47.880259),  # 4.448 22 N / 92 903.04 mm² = 4.788 03e-5 MPa = 47.880 Pa
        ("1 psi", "kPa", 6.8947573),  # 4.448 22 N / 645.16 mm² = 0.006 894 76 MPa
        ("1 ksi", "MPa", 6.8947573),
        ("1 ksf", "kPa", 47.880259),
        ("12 GPa", "MPa", 12000.0),
        ("1 plf", "N/m", 14.593903),  # 4.448 22 N / 304.8 mm = 0.014 594 N/mm = 14.594 N/m
        ("1 klf", "kN/m", 14.593903),
        ("1 pcf", "kN/m³", 0.15708746),  # 4.448 22 N / 28 316 846.6 mm³ = 1.5709e-7 N/mm³
        # Mêmes règles que les champs (lire_grandeur)
        ("8'2\"", "po", 98.0),  # le 2 après ' est des pouces, pas un exposant
        ("8 pi 6", "po", 102.0),
        ("3 pi 2 1/4 po", "mm", 971.55),  # 914.4 mm + 57.15 mm
        ("2 + 3 po", "po", 5.0),
        ("(2+3)/2 po", "po", 2.5),
        ("(2+3)/2 kN/m", "kN/m", 2.5),
        ("50% de 4 kn", "kN", 2.0),
        ("1,5 m -> mm", None, 1500.0),
        ("40 000 lb en kN", None, 177.92886),  # 40 000 x 4.448 22 N = 177 928.86 N
        # « / » de gauche à droite (pas comme « sur ») : 400 lb / 3 po x 3 po = 400 lb
        ("400 lb / 3 po x 3 po", "lb", 400.0),
    ],
)
def test_calculer(texte, unite, attendu):
    calcul = calculer(texte)
    assert calcul.dans(unite or calcul.unite_demandee) == pytest.approx(attendu, rel=1e-6)


@pytest.mark.parametrize(
    "texte, nom",
    [
        ("3 po", "longueur"),
        ("3 po * 4 po", "aire"),
        ("3 po^3", "volume ou module de section"),
        ("3 po^4", "moment d'inertie"),
        ("3 lb", "force"),
        ("3 lb·pi", "moment"),
        ("3 plf", "charge répartie"),
        ("3 psf", "pression ou contrainte"),
        ("3 pcf", "poids volumique"),
        ("2x10", "nombre"),
        ("3 kN / po^4", "N/mm⁴"),  # dimension sans nom : unité de base
    ],
)
def test_nom_de_la_dimension(texte, nom):
    assert calculer(texte).nom == nom


def test_valeur_de_base_et_unites_proposees():
    calcul = calculer("3 kN/m")
    assert calcul.valeur == pytest.approx(3.0)  # N/mm
    assert calcul.dimension == (-1, 1)
    assert calcul.unite_demandee is None
    assert "lb/pi" in calcul.unites_proposees
    for unite in calcul.unites_proposees:  # chaque unité proposée se lit et convient
        calcul.dans(unite)
    assert calculer("3 kN / po^4").unites_proposees == ()


@pytest.mark.parametrize(
    "texte, message",
    [
        ("3 po + 2 kN", "addition d'unités incompatibles"),
        ('8" x 600 mm en pi', "mm² ne peut pas être affiché en pi"),
        ("3 po en kN", "mm ne peut pas être affiché en kN"),
        ("5 en truc", "unité inconnue : truc"),
        ("", "valeur vide"),
        ("   ?", "valeur vide"),
        ("3 po / 0", "division par zéro"),
        ("3 truc", "texte illisible"),
        ("2 ^ 1.5", "exposant invalide"),
        ("2 ^ (3 po)", "exposant invalide"),
        ("(3 po", "texte illisible"),
    ],
)
def test_refus(texte, message):
    with pytest.raises(ValueError, match=message):
        calculer(texte)


def test_dans_une_unite_inconnue_ou_incompatible():
    calcul = calculer("3 kN")
    assert calcul.dans("lb") == pytest.approx(3000 / LB)  # 674.43 lb
    with pytest.raises(ValueError, match="unité inconnue"):
        calcul.dans("truc")
    with pytest.raises(ValueError, match="N ne peut pas être affiché en m"):
        calcul.dans("m")
