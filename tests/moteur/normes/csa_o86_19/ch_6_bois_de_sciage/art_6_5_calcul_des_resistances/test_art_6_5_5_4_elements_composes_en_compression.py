"""
Tests de 6.5.5.4 Éléments composés en compression (p. 70-71, issue #32).

Décisions de l'utilisateur (issue #32, 27 novembre 2026) : coefficient de réduction selon b seulement
(6.5.5.4.6), assemblage non vérifié (exigences en notes), calcul refusé hors de 6.5.5.4.1, K_H = 1,00.

Valeurs calculées à la main. Bois : 2x6 S-P-F n° 1/n° 2 sec (tableau 6.4 : f_c = 11,5 MPa,
E_05 = 6500 MPa), plis de 38 mm x 140 mm, tous les coefficients K = 1, K_e = 1. Constantes utiles :
    35 x E_05 x K_SE x K_T = 35 x 6500 MPa = 227 500 MPa ; phi F_c = 0,8 x 11,5 MPa = 9,2 MPa.
"""

import pytest

from moteur.commun import registre
from moteur.commun.figures import figure, figure_avant_le_calcul
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage import art_6_4_coefficients_de_correction as art_6_4
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art,
)

F_C = 11.5  # MPa
E_05 = 6500  # MPa


def _compose(nombre_de_plis, L, L_selon_b, L_selon_d, assemblage, P_f=None, largeur_d_un_pli=38, d=140):
    return art.verifier_compression_parallele_element_compose(
        largeur_d_un_pli=largeur_d_un_pli, nombre_de_plis=nombre_de_plis, d=d, L=L,
        L_selon_b=L_selon_b, L_selon_d=L_selon_d, f_c=F_C, E_05=E_05, assemblage=assemblage, P_f=P_f,
    )


# --- fonctions simples ---
def test_verifier_les_plis():
    # 6.5.5.4.1 : 2 à 5 plis d'au moins 38 mm ; limites exactes acceptées
    for nombre_de_plis in (2, 3, 4, 5):
        art.verifier_les_plis(nombre_de_plis, 38)  # 38 mm : exactement la limite
    art.verifier_les_plis(2, 89)  # 89 mm
    # Hors limites : calcul refusé (décision de l'utilisateur)
    for nombre_de_plis, largeur in ((1, 38), (6, 38), (0, 38), (2, 37.9), (3, 19)):  # mm
        with pytest.raises(ValueError, match="6.5.5.4.1"):
            art.verifier_les_plis(nombre_de_plis, largeur)


def test_coefficient_de_reduction():
    assert art.coefficient_de_reduction(art.CLOUS) == 0.60  # 6.5.5.4.2 : 60 %
    assert art.coefficient_de_reduction(art.BOULONS) == 0.75  # 6.5.5.4.3 : 75 %
    assert art.coefficient_de_reduction(art.ANNEAUX_FENDUS) == 0.80  # 6.5.5.4.4 : 80 %
    for inconnu in ("colle", "", "CLOUS"):
        with pytest.raises(ValueError):
            art.coefficient_de_reduction(inconnu)


def test_resistance_reduite_et_combinee():
    assert art.resistance_reduite(0.60, 25_000) == pytest.approx(15_000)  # 0,60 x 25 000 N = 15 000 N
    assert art.resistance_combinee_des_pieces_individuelles(3, 12_620) == 37_860  # 3 x 12 620 N
    assert art.resistance_combinee_des_pieces_individuelles(2, 0) == 0


def test_P_r_element_compose():
    # 6.5.5.4.1 : la plus grande des deux valeurs
    assert art.P_r_element_compose(15_000, 10_000) == 15_000  # N
    assert art.P_r_element_compose(15_000, 20_000) == 20_000  # N
    assert art.P_r_element_compose(15_000, 15_000) == 15_000  # égalité
    assert art.P_r_element_compose(15_000, None) == 15_000  # plis individuels non permis (C_C > 50)


def test_K_H_en_compression_pour_un_element_compose():
    # Décision #7 et issue #32 : colonne « Poutres composées » du tableau 6.12 (p. 62) : 1,00 en
    # compression parallèle, même si le cas 1 ou le cas 2 serait respecté
    cas = art_6_4.cas_de_systeme(True, True, poutre_composee=True)
    assert art_6_4.K_H(art_6_4.COMPRESSION_PARALLELE, cas) == 1.00
    assert art_6_4.K_H(art_6_4.COMPRESSION_PARALLELE, cas, msr=True) == 1.00


# --- vérification ---
def test_2_plis_cloues_plis_individuels_trop_elances():
    """
    2-2x6 cloués, L = L_(b) = L_(d) = 3000 mm. b = 2 x 38 mm = 76 mm ; A = 76 mm x 140 mm = 10 640 mm².
    Selon b : C_C = 3000 mm / 76 mm = 39,474 ; K_Zc = 6,3 (76 mm x 3000 mm)^-0,13 = 6,3 x 0,201114 = 1,26702
        K_C = [1 + 11,5 x 1,26702 x 39,474^3 / 227 500]^-1 = [1 + 3,93933]^-1 = 0,202457
        massif : 9,2 MPa x 10 640 mm² x 1,26702 x 0,202457 = 25 110 N ; x 0,60 = 15 066 N
        plis : C_C = 3000 mm / 38 mm = 78,9 > 50 : non permis -> P_r(b) = 15 066 N
    Selon d (coefficient omis, 6.5.5.4.6) : C_C = 21,4286, K_Zc = 1,1704, K_C = 0,63206
        P_r(d) = 9,2 MPa x 10 640 mm² x 1,1704 x 0,63206 = 72 41x N
    P_r = 15 066 N.
    """
    r = _compose(2, 3000, 3000, 3000, art.CLOUS, P_f=10.0)
    assert r.article == "6.5.5.4"
    assert r.etape("C_{C(b)}").valeur == pytest.approx(39.474, rel=1e-4)
    assert r.etape("K_{Zc(b)}").valeur == pytest.approx(1.26702, rel=1e-4)
    assert r.etape("K_{C(b)}").valeur == pytest.approx(0.202457, rel=1e-4)
    assert r.etape("P_{r(b)}").valeur == pytest.approx(15_066, rel=1e-3)
    assert r.etape("P_{r(d)}").valeur == pytest.approx(72_414, rel=1e-3)
    assert r.etape("P_r").valeur == pytest.approx(15_066, rel=1e-3)
    # Les plis individuels ne sont pas calculés : une note dit pourquoi (6.5.5.2.2)
    assert not [e for e in r.etapes if "pli" in e.description]
    assert any("78.95 > 50" in n for n in r.notes)
    # 10 kN / 15,066 kN = 0,664
    assert r.verification.ratio == pytest.approx(0.6637, rel=1e-3)
    assert r.verification.respecte


def test_3_plis_boulonnes_selon_d_gouverne():
    """
    3-2x6 boulonnés, L = 3000 mm, L_(b) = 1500 mm, L_(d) = 3000 mm. b = 114 mm ; A = 15 960 mm².
    Selon b : C_C = 1500 mm / 114 mm = 13,158 ; K_Zc = 6,3 (114 mm x 3000 mm)^-0,13 = 1,20197
        K_C = [1 + 11,5 x 1,20197 x 13,158^3 / 227 500]^-1 = [1 + 0,138409]^-1 = 0,878418
        massif : 9,2 MPa x 15 960 mm² x 1,20197 x 0,878418 = 155 030 N ; x 0,75 = 116 272 N
        un pli : C_C = 1500 mm / 38 mm = 39,474 ; K_Zc(38 mm, 3000 mm) = 1,3868 -> 1,3
            K_C = [1 + 11,5 x 1,3 x 39,474^3 / 227 500]^-1 = [1 + 4,04187]^-1 = 0,198340
            P_r = 9,2 MPa x 5320 mm² x 1,3 x 0,198340 = 12 620 N ; 3 plis : 37 860 N
        P_r(b) = max(116 272 N ; 37 860 N) = 116 272 N
    Selon d : P_r(d) = 9,2 MPa x 15 960 mm² x 1,1704 x 0,63206 = 108 62x N -> gouverne.
    """
    r = _compose(3, 3000, 1500, 3000, art.BOULONS, P_f=5.0)
    reduite = [e for e in r.etapes if e.article == "6.5.5.4.3"][0]
    assert reduite.valeur == pytest.approx(116_272, rel=1e-3)
    combinee = [e for e in r.etapes if e.description.startswith("Résistance combinée")][0]
    assert combinee.valeur == pytest.approx(37_860, rel=1e-3)
    assert r.etape("P_{r(b)}").valeur == pytest.approx(116_272, rel=1e-3)
    assert r.etape("P_{r(d)}").valeur == pytest.approx(108_621, rel=1e-3)
    assert r.etape("P_r").valeur == pytest.approx(108_621, rel=1e-3)
    # Selon d, aucun coefficient de réduction (6.5.5.4.6) : P_r(d) = P_r de l'élément massif
    assert r.etape("P_{r(d)}").article == "6.5.5.4.6"


def test_2_plis_cloues_courts_plis_individuels_gouvernent():
    """
    2-2x6 cloués, L = L_(b) = L_(d) = 600 mm. Les plis individuels donnent plus que 60 % du massif.
    Selon b : C_C = 600 mm / 76 mm = 7,8947 ; K_Zc = 6,3 (76 x 600)^-0,13 = 1,5619 -> 1,3
        K_C = [1 + 11,5 x 1,3 x 7,8947^3 / 227 500]^-1 = [1 + 0,032334]^-1 = 0,968679
        massif : 9,2 MPa x 10 640 mm² x 1,3 x 0,968679 = 123 269 N ; x 0,60 = 73 961 N
        un pli : C_C = 600 mm / 38 mm = 15,789 ; K_Zc = 1,3 ; K_C = [1 + 0,258681]^-1 = 0,794483
            9,2 MPa x 5320 mm² x 1,3 x 0,794483 = 50 551 N ; 2 plis : 101 102 N
        P_r(b) = max(73 961 N ; 101 102 N) = 101 102 N
    Selon d : C_C = 600 mm / 140 mm = 4,2857 ; K_Zc = 6,3 (140 x 600)^-0,13 = 1,44261 -> 1,3
        K_C = [1 + 11,5 x 1,3 x 4,2857^3 / 227 500]^-1 = [1 + 0,0051728]^-1 = 0,994854
        P_r(d) = 9,2 MPa x 10 640 mm² x 1,3 x 0,994854 = 126 600 N
    P_r = 101 102 N.
    """
    r = _compose(2, 600, 600, 600, art.CLOUS)
    assert [e for e in r.etapes if e.article == "6.5.5.4.2"][0].valeur == pytest.approx(73_961, rel=1e-3)
    assert r.etape("P_{r(b)}").valeur == pytest.approx(101_102, rel=1e-3)
    assert r.etape("P_{r(d)}").valeur == pytest.approx(126_600, rel=1e-3)
    assert r.etape("P_r").valeur == pytest.approx(101_102, rel=1e-3)
    assert r.verification is None  # pas de P_f


def test_anneaux_fendus_ratio_exactement_1():
    # 2-2x6, 3000 mm : massif selon b = 25 110 N (voir plus haut) ; x 0,80 = 20 088 N
    r = _compose(2, 3000, 3000, 3000, art.ANNEAUX_FENDUS)
    assert r.etape("P_r").valeur == pytest.approx(20_088, rel=1e-3)
    # P_f = P_r : ratio = 1,00, état limite respecté (5.1.2)
    r = _compose(2, 3000, 3000, 3000, art.ANNEAUX_FENDUS, P_f=r.etape("P_r").valeur / 1000)
    assert r.verification.ratio == pytest.approx(1.0)
    assert r.verification.respecte


def test_calcul_refuse():
    # 6.5.5.4.1 : 1 pli, 6 plis, plis de moins de 38 mm (décision de l'utilisateur : calcul refusé)
    for nombre_de_plis, largeur in ((1, 38), (6, 38), (2, 35)):  # mm
        with pytest.raises(ValueError, match="6.5.5.4.1"):
            _compose(nombre_de_plis, 3000, 3000, 3000, art.CLOUS, largeur_d_un_pli=largeur)
    with pytest.raises(ValueError):
        _compose(2, 3000, 3000, 3000, "colle")
    # Élément trop élancé selon b : C_C = 4000 mm / 76 mm = 52,6 > 50 (6.5.5.2.2)
    with pytest.raises(ValueError, match="50"):
        _compose(2, 4000, 4000, 3000, art.CLOUS)


def test_exigences_de_l_assemblage():
    # Clous, 2x6 : 6 x 38 mm = 228 mm ; d = 140 mm > 3 x 38 mm = 114 mm : deux rangées requises
    clous = art.exigences_de_l_assemblage(art.CLOUS, 38, 140)
    assert clous[0].startswith("Datum ne vérifie pas")
    assert any(n.startswith("6.5.5.4.1") and "1.2 fois" in n for n in clous)
    assert [n[:12] for n in clous[2:]] == ["6.5.5.4.2 a)", "6.5.5.4.2 b)", "6.5.5.4.2 c)"]
    assert "228 mm (8.98 po)" in clous[2] and "20 fois le diamètre" in clous[2]
    assert "au moins deux rangées sont requises" in clous[4]
    # 2x4 : d = 89 mm <= 114 mm : pas exigé
    assert "pas exigé" in art.exigences_de_l_assemblage(art.CLOUS, 38, 89)[4]
    # Exactement 3 fois : 114 mm n'est pas « supérieure à » 114 mm
    assert "pas exigé" in art.exigences_de_l_assemblage(art.BOULONS, 38, 114)[-1]
    boulons = art.exigences_de_l_assemblage(art.BOULONS, 38, 140)
    assert any("6 mm (1/4 po)" in n for n in boulons)
    assert any("10 fois le diamètre" in n for n in boulons)
    anneaux = art.exigences_de_l_assemblage(art.ANNEAUX_FENDUS, 38, 140)
    assert any("12 mm (1/2 po)" in n and "63 mm (2 1/2 po)" in n and "228 mm" in n for n in anneaux)
    with pytest.raises(ValueError):
        art.exigences_de_l_assemblage("colle", 38, 140)


def test_notes_et_donnees_dans_la_trace():
    r = _compose(3, 3000, 1500, 3000, art.BOULONS)
    assert r.notes == art.exigences_de_l_assemblage(art.BOULONS, 38, 140)
    donnees = {(d.symbole, d.description): d for d in r.donnees}
    assert donnees[("b", "Largeur de l'élément (plis compris)")].valeur == 114  # 3 x 38 mm (#95)
    assert donnees[("", "Nombre de plis")].valeur == 3  # pas de symbole dans la norme
    assert donnees[("", "Assemblage des plis")].source == "6.5.5.4.3"


def test_registre_et_figure():
    assert "6.5.5.4" in {c.identifiant for c in registre.calculs("csa_o86_19")}
    r = _compose(3, 3000, 1500, 3000, art.BOULONS)
    assert figure(r) is not None
    assert figure_avant_le_calcul("6.5.5.4", 3) is not None
