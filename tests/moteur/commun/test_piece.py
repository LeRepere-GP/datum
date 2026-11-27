"""
Tests de moteur/commun/piece.py : lecture du texte de la boîte « Pièce » (datum-retours #20).

Valeurs attendues calculées à la main (ex. 5 1/4 po = 5 + 1/4 = 5.25 po ; 8 7/16 po = 8 + 7/16 = 8.4375 po).
"""

import re

import pytest

from moteur.commun.piece import lire_piece


# (texte, plis, largeur d'un pli entrée, hauteur entrée, en mm, vert, brut)
@pytest.mark.parametrize(
    "texte, plis, largeur, hauteur, en_mm, vert, brut",
    [
        # Exemples de l'utilisateur (#20)
        ("2x10", 1, 2, 10, False, False, False),
        ("2 2x6", 2, 2, 6, False, False, False),
        ("4x4 vert", 1, 4, 4, False, True, False),
        ("5 1/4 x 8 7/16 brut", 1, 5.25, 8.4375, False, False, True),  # 5 + 1/4 po ; 8 + 7/16 po
        # Autres écritures des plis
        ("2-2x6", 2, 2, 6, False, False, False),
        ("2 - 2x6", 2, 2, 6, False, False, False),
        ("3 plis de 2x8", 3, 2, 8, False, False, False),
        ("5 2x6", 5, 2, 6, False, False, False),  # limite : 5 plis permis
        # Nombres fractionnaires : pas des plis (fraction après l'entier)
        ("5 1/4 x 8 7/16", 1, 5.25, 8.4375, False, False, False),
        ("2 1/2 x 6", 1, 2.5, 6, False, False, False),  # 2 + 1/2 po, pas 2 plis de 1/2 po
        ("1-1/2 x 5-1/2", 1, 1.5, 5.5, False, False, False),  # écriture de l'affichage de Datum
        ("3 2 1/2 x 6", 3, 2.5, 6, False, False, False),  # 3 plis de 2 1/2 x 6 po
        ("7/8 x 6", 1, 0.875, 6, False, False, False),  # 7/8 po = 0.875 po
        # Décimales, séparateurs, majuscules, unités
        ("5.25 x 8.4375", 1, 5.25, 8.4375, False, False, False),
        ("5,25 x 8,4375", 1, 5.25, 8.4375, False, False, False),  # virgule décimale
        ("2X6", 1, 2, 6, False, False, False),
        ("2×6", 1, 2, 6, False, False, False),
        ("2*6", 1, 2, 6, False, False, False),
        ("  2 x 6  ", 1, 2, 6, False, False, False),
        ('5 1/4" x 8"', 1, 5.25, 8, False, False, False),
        ("2x6 po", 1, 2, 6, False, False, False),
        ("4X4VERT", 1, 4, 4, False, True, False),
        ("4x4 verte", 1, 4, 4, False, True, False),
        ("2x6 sec", 1, 2, 6, False, False, False),
        ("2x6 sèche", 1, 2, 6, False, False, False),
        ("2x6 vert brut", 1, 2, 6, False, True, True),
        # Millimètres : dimensions réelles
        ("89 x 140 mm", 1, 89, 140, True, False, False),
        ("89x140mm", 1, 89, 140, True, False, False),
        ("2 38x235 mm", 2, 38, 235, True, False, False),
        ("88.9 x 139.7 mm", 1, 88.9, 139.7, True, False, False),
    ],
)
def test_lire_piece(texte, plis, largeur, hauteur, en_mm, vert, brut):
    piece = lire_piece(texte)
    assert piece.texte == texte
    assert piece.nombre_de_plis == plis
    assert piece.largeur_d_un_pli_entree == pytest.approx(largeur)
    assert piece.hauteur_entree == pytest.approx(hauteur)
    assert (piece.en_mm, piece.vert, piece.brut) == (en_mm, vert, brut)


def test_texte_des_dimensions_garde_pour_l_affichage():
    piece = lire_piece("5  1/4 x 8 7/16")
    assert (piece.texte_largeur, piece.texte_hauteur) == ("5 1/4", "8 7/16")  # espaces simplifiés


@pytest.mark.parametrize(
    "texte, raison",
    [
        ("", "entrez la pièce"),
        ("   ", "entrez la pièce"),
        ("2x6 spf", "le mot « spf » n'est pas reconnu"),  # jamais de mot ignoré en silence
        ("abc", "le mot « abc » n'est pas reconnu"),
        ("2x6 vert sec", "« vert » et « sec »"),
        ("38 mm x 6 po", "deux unités"),
        ("2x6x8", "n'a pas la forme"),
        ("2x", "n'a pas la forme"),
        ("x6", "n'a pas la forme"),
        ("2 6", "n'a pas la forme"),
        ("6 2x6", "de 1 à 5 (6 entré)"),  # limite : 6 plis refusés
        ("0 2x6", "de 1 à 5 (0 entré)"),
        ("0x6", "dimension nulle"),
        ("2x0 mm", "dimension nulle"),
        ("1/0 x 6", "dénominateur nul"),
    ],
)
def test_texte_refuse(texte, raison):
    with pytest.raises(ValueError, match=re.escape(raison)):
        lire_piece(texte)
