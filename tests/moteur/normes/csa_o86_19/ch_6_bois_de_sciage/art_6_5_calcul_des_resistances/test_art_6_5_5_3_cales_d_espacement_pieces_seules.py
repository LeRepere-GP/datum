"""
Tests de 6.5.5.3 Éléments en compression assemblés avec cales d'espacement, pièces calculées seules par
6.5.5.2, sans gain des cales (p. 69 ; réponse de l'utilisateur à la question 3 de l'issue #115).

Valeurs calculées à la main. 2 pièces 2x6 S-P-F n° 1/n° 2 sec (f_c = 11,5 MPa, E_05 = 6500 MPa),
38 mm x 140 mm, L = L_(b) = L_(d) = 1500 mm, K_e = 1, tous les coefficients K = 1.
    phi F_c x aire d'une pièce = 0,8 x 11,5 MPa x 5320 mm² = 48 944 N ; 35 E_05 = 227 500 MPa.
"""

import pytest

from moteur.commun import registre
from moteur.commun.figures import figure
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art,
)


def _pieces(nombre_de_pieces=2, L=1500, P_f=None):
    return art.verifier_compression_pieces_seules_avec_cales_d_espacement(
        largeur_d_une_piece=38, nombre_de_pieces=nombre_de_pieces, d=140, L=L, L_selon_b=L, L_selon_d=L,
        f_c=11.5, E_05=6500, P_f=P_f,
    )


def test_somme_des_pieces_seules():
    r = _pieces()
    assert r.article == "6.5.5.3"
    # Selon b : C_C = 1500 mm / 38 mm = 39,47 ; K_Zc = 6,3 (38 mm x 1500 mm)^-0,13 = 1,517 -> 1,3 ;
    # K_C = [1 + 11,5 x 1,3 x 39,47³ / 227 500]^-1 = [1 + 4,0418]^-1 = 0,19834 ;
    # P_r(b) = 48 944 N x 1,3 x 0,19834 = 12 620 N
    assert r.etape("K_{Zc(b)}").valeur == 1.3
    assert r.etape("K_{C(b)}").valeur == pytest.approx(0.19834, abs=1e-4)
    assert r.etape("P_{r(b)}").valeur == pytest.approx(12_620, rel=1e-3)
    # Selon d : C_C = 10,71 ; K_Zc = 6,3 (140 mm x 1500 mm)^-0,13 = 1,2807 ; K_C = 0,92625 ;
    # P_r(d) = 48 944 N x 1,2807 x 0,92625 = 58 061 N
    assert r.etape("P_{r(d)}").valeur == pytest.approx(58_061, rel=1e-3)
    # Élément : 2 x 12 620 N = 25 240 N
    assert r.etape("P_r").valeur == pytest.approx(25_240, rel=1e-3)
    # Une seule étape porte le symbole P_r : celle de l'élément
    assert [e.symbole for e in r.etapes].count("P_r") == 1
    assert any(d.description == "Nombre de pièces" and d.valeur == 2 for d in r.donnees)
    assert "A.6.5.5.3" in r.notes[0]


def test_trois_pieces_et_ratio_au_seuil():
    trois = _pieces(nombre_de_pieces=3)
    assert trois.etape("P_r").valeur == pytest.approx(3 * 12_620, rel=1e-3)
    p_r = trois.etape("P_r").valeur  # N
    assert _pieces(nombre_de_pieces=3, P_f=p_r / 1000).verification.ratio == pytest.approx(1.0)


def test_calcul_refuse():
    with pytest.raises(ValueError, match="A.6.5.5.3.1"):
        _pieces(nombre_de_pieces=1)
    with pytest.raises(ValueError, match="50"):
        _pieces(L=3000)  # C_C(b) d'une pièce = 3000 mm / 38 mm = 78,9 > 50 (6.5.5.2.2)


def test_registre_et_figure():
    assert registre.calcul("csa_o86_19", "6.5.5.3").fonction is (
        art.verifier_compression_pieces_seules_avec_cales_d_espacement
    )
    assert figure(_pieces()).startswith("<svg")
