"""
Tests de A.6.5.5.3 Éléments en compression assemblés avec cales d'espacement (annexe A, p. 305-308,
issue #115).

Valeurs calculées à la main. Bois : 2x6 S-P-F n° 1/n° 2 sec (tableau 6.4 : f_c = 11,5 MPa,
E_05 = 6500 MPa), pièces de 38 mm x 140 mm, cales de 38 mm, tous les coefficients K = 1. Constantes :
    phi F_c = 0,8 x 11,5 MPa = 9,2 MPa ; aire d'une pièce = 38 mm x 140 mm = 5320 mm² ;
    35 x E_05 x K_SE x K_T = 35 x 6500 MPa = 227 500 MPa.
"""

import pytest

from moteur.commun import registre
from moteur.commun.figures import figure
from moteur.normes.csa_o86_19.annexe_A_renseignements_supplementaires_et_autres_methodes.art_A_6_bois_de_sciage import (
    art_A_6_5_5_3_elements_en_compression_assembles_avec_cales_d_espacement as art,
)

F_C = 11.5  # MPa
E_05 = 6500  # MPa


def _cales(L_selon_b=3000, L_selon_d=3000, nombre_de_pieces=2, distance_des_connecteurs=150, L=3000, P_f=None,
           epaisseur_des_cales=38, groupe_d_essences="spf"):
    return art.verifier_compression_element_avec_cales_d_espacement(
        largeur_d_une_piece=38, nombre_de_pieces=nombre_de_pieces, d=140,
        epaisseur_des_cales=epaisseur_des_cales, L=L, L_selon_b=L_selon_b, L_selon_d=L_selon_d,
        f_c=F_C, E_05=E_05, distance_des_connecteurs=distance_des_connecteurs, groupe_d_essences=groupe_d_essences, P_f=P_f,
    )


def _etape(resultat, description_debut):
    """Valeur de l'étape dont la description commence par ce texte."""
    for etape in resultat.etapes:
        if etape.description.startswith(description_debut):
            return etape.valeur
    raise KeyError(description_debut)


# --- Fonctions simples ---
def test_verifier_les_pieces():
    # A.6.5.5.3.1 : au moins 2 pièces, pas de maximum
    for nombre in (2, 3, 6):
        art.verifier_les_pieces(nombre)
    for nombre in (0, 1):
        with pytest.raises(ValueError, match="A.6.5.5.3.1"):
            art.verifier_les_pieces(nombre)


def test_condition_de_retenue():
    # L = 3000 mm : L / 20 = 150 mm, L / 10 = 300 mm
    assert art.condition_de_retenue(50, 3000) == "A"
    assert art.condition_de_retenue(150, 3000) == "A"  # L / 20 exactement : « within 1/20 » (anglais)
    assert art.condition_de_retenue(150.1, 3000) == "B"
    assert art.condition_de_retenue(300, 3000) == "B"  # L / 10 exactement
    with pytest.raises(ValueError, match="L / 10"):
        art.condition_de_retenue(300.1, 3000)  # au-delà de L / 10 : calcul refusé
    with pytest.raises(ValueError):
        art.condition_de_retenue(0, 3000)


def test_K_E():
    # A.6.5.5.3.5.4 : 2,50 pour la condition A, 3,00 pour la condition B
    assert art.K_E("A") == 2.50
    assert art.K_E("B") == 3.00
    with pytest.raises(ValueError, match="A.6.5.5.3.3"):
        art.K_E("C")


def test_F_c_sans_K_H():
    # F_c = f_c (K_D K_Sc K_T) : 10 MPa x (0,65 x 0,9 x 1,0) = 5,85 MPa (pas de K_H)
    assert art.F_c(10, K_D=0.65, K_Sc=0.9, K_T=1.0) == pytest.approx(5.85)
    assert art.F_c(11.5) == 11.5


def test_dimension_hors_tout():
    # 2 pièces de 38 mm + 1 cale de 38 mm = 114 mm ; 3 pièces de 38 mm + 2 cales de 19 mm = 152 mm
    assert art.dimension_hors_tout(2, 38, 38) == 114
    assert art.dimension_hors_tout(3, 38, 19) == 152
    with pytest.raises(ValueError):
        art.dimension_hors_tout(2, 38, 0)


def test_C_C_limite_de_80():
    # 3000 mm / 38 mm = 78,95 ; 3040 mm / 38 mm = 80 exactement : permis ; 3050 mm / 38 mm = 80,26 : refusé
    assert art.C_C(3000, 38) == pytest.approx(78.947, abs=1e-3)
    assert art.C_C(3040, 38) == pytest.approx(80)
    with pytest.raises(ValueError, match="80"):
        art.C_C(3050, 38)
    with pytest.raises(ValueError):
        art.C_C(0, 38)


def test_C_K():
    # Condition A : racine(0,76 x 6500 MPa x 2,50 / 11,5 MPa) = racine(1073,91) = 32,771
    assert art.C_K(F_C, E_05, 2.50) == pytest.approx(32.771, abs=1e-3)
    # Condition B : racine(0,76 x 6500 MPa x 3,00 / 11,5 MPa) = racine(1288,70) = 35,898
    assert art.C_K(F_C, E_05, 3.00) == pytest.approx(35.898, abs=1e-3)


def test_K_C_trois_branches():
    c_k = 32.771
    # a) C_C <= 10 : 1,00 (10 exactement compris)
    assert art.K_C(10, c_k, F_C, E_05, 2.5) == 1.00
    assert art.K_C(5, c_k, F_C, E_05, 2.5) == 1.00
    # b) 10 < C_C <= C_K : 1 - (1/3)(20 / 32,771)^4 = 1 - (1/3)(0,13873) = 0,95376
    assert art.K_C(20, c_k, F_C, E_05, 2.5) == pytest.approx(0.95376, abs=1e-4)
    # Égalité C_C = C_K : branche b) (anglais : « does not exceed C_K ») : 1 - 1/3 = 0,6667
    assert art.K_C(c_k, c_k, F_C, E_05, 2.5) == pytest.approx(2 / 3)
    # c) C_K < C_C <= 80 : 6500 MPa x 2,5 / (1,8 x 78,947² x 11,5 MPa) = 16 250 / 129 017 = 0,12595
    assert art.K_C(3000 / 38, c_k, F_C, E_05, 2.5) == pytest.approx(0.12595, abs=1e-4)
    # Juste au-dessus de C_K : branche c), 1 / (1,8 x 0,76) x (C_K / C_C)² = 0,731 (saut permis par la norme)
    assert art.K_C(c_k * 1.0001, c_k, F_C, E_05, 2.5) == pytest.approx(0.7310, abs=1e-3)
    with pytest.raises(ValueError, match="80"):
        art.K_C(81, c_k, F_C, E_05, 2.5)


def test_C_C_d_une_piece_seule():
    # 3000 mm / 140 mm = 21,43 ; limite de 6.5.5.2.2 : 7000 mm / 140 mm = 50 permis, 7100 mm refusé
    assert art.C_C_d_une_piece_seule(3000, 140) == pytest.approx(21.4286, abs=1e-4)
    assert art.C_C_d_une_piece_seule(7000, 140) == pytest.approx(50)
    with pytest.raises(ValueError, match="50"):
        art.C_C_d_une_piece_seule(7100, 140)


def test_P_r_la_moindre():
    # A.6.5.5.3.5.1 : la moindre des deux (et non la plus grande comme en 6.5.5.4.1)
    assert art.P_r_element_assemble(14_820, 72_411) == 14_820  # N
    assert art.P_r_element_assemble(83_850, 72_411) == 72_411  # N


def test_constante_du_tableau_A_5():
    # Lignes exactes et extrémités
    assert art.constante_du_tableau_A_5(0, "df") == 0.00
    assert art.constante_du_tableau_A_5(10, "spf") == 0.00
    assert art.constante_du_tableau_A_5(15, "hf") == 0.30
    assert art.constante_du_tableau_A_5(50, "ns") == 1.9
    for c_c in (60, 70, 80):  # ligne « 60 à 80 »
        assert art.constante_du_tableau_A_5(c_c, "df") == 3.8
    # Interpolation : C_C = 12,5 (D.Fir-L) : 0 + 0,5 x 0,38 = 0,19 MPa
    assert art.constante_du_tableau_A_5(12.5, "df") == pytest.approx(0.19)
    # C_C = 57,5 (Hem-Fir) : (2,8 + 3,0) / 2 = 2,9 MPa
    assert art.constante_du_tableau_A_5(57.5, "hf") == pytest.approx(2.9)
    # C_C = 78,95 (É-P-S) : 2,6 MPa (ligne 60 à 80)
    assert art.constante_du_tableau_A_5(78.95, "spf") == 2.6
    with pytest.raises(ValueError, match="A.5"):
        art.constante_du_tableau_A_5(30, "msr")
    with pytest.raises(ValueError):
        art.constante_du_tableau_A_5(81, "df")


def test_resistance_requise_des_connecteurs():
    # 5320 mm² x 2,6 MPa = 13 832 N
    assert art.resistance_requise_des_connecteurs(5320, 2.6) == pytest.approx(13_832)


# --- Vérification ---
def test_poteau_elance_l_element_assemble_gouverne():
    # L = L_(b) = L_(d) = 3000 mm, condition A
    r = _cales()
    assert _etape(r, "Aire") == 10_640  # 2 x 38 mm x 140 mm = 10 640 mm²
    assert r.etape("C_{C(b)}").valeur == pytest.approx(78.947, abs=1e-3)
    assert _etape(r, "Dimension de l'élément") == 114  # mm
    # K_Zc(b) = 6,3 (114 mm x 3000 mm)^-0,13 = 6,3 x 0,19082 = 1,2022
    assert r.etape("K_{Zc(b)}").valeur == pytest.approx(1.2022, abs=1e-3)
    assert r.etape("C_K").valeur == pytest.approx(32.771, abs=1e-3)
    assert r.etape("K_{C(b)}").valeur == pytest.approx(0.12595, abs=1e-4)
    # P_r(b) = 0,8 x 11,5 MPa x 10 640 mm² x 0,12595 x 1,2022 = 14 822 N
    assert r.etape("P_{r(b)}").valeur == pytest.approx(14_822, rel=1e-3)
    # Pièces seules : C_C(d) = 21,43 ; K_Zc(d) = 6,3 (140 mm x 3000 mm)^-0,13 = 1,1705 ;
    # K_C(d) = [1 + 11,5 x 1,1705 x 21,43³ / 227 500]^-1 = [1 + 0,58218]^-1 = 0,63204
    assert r.etape("K_{Zc(d)}").valeur == pytest.approx(1.1705, abs=1e-3)
    assert r.etape("K_{C(d)}").valeur == pytest.approx(0.63204, abs=1e-3)
    # 2 x 0,8 x 11,5 MPa x 5320 mm² x 1,1705 x 0,63204 = 2 x 36 209 N = 72 418 N
    assert r.etape("P_{r(d)}").valeur == pytest.approx(72_418, rel=1e-3)
    # La moindre : l'élément assemblé
    assert r.etape("P_r").valeur == pytest.approx(14_822, rel=1e-3)
    # Information : constante É-P-S à C_C = 78,95 : 2,6 MPa ; 5320 mm² x 2,6 MPa = 13 832 N
    assert _etape(r, "Résistance pondérée requise") == pytest.approx(13_832)


def test_poteau_contreventé_selon_b_les_pieces_gouvernent():
    # L_(b) = 1200 mm : C_C(b) = 31,58 < C_K = 32,77, branche b) :
    # K_C(b) = 1 - (1/3)(31,58 / 32,77)^4 = 1 - (1/3)(0,8625) = 0,7125
    # P_r(b) = 97 888 N x 0,7125 x 1,2022 = 83 848 N > P_r(d) = 72 418 N : les pièces gouvernent
    r = _cales(L_selon_b=1200, distance_des_connecteurs=50)  # 50 mm <= 1200 mm / 20 = 60 mm : A
    assert r.etape("K_{C(b)}").valeur == pytest.approx(0.7125, abs=1e-3)
    assert r.etape("P_{r(b)}").valeur == pytest.approx(83_848, rel=2e-3)
    assert r.etape("P_r").valeur == pytest.approx(r.etape("P_{r(d)}").valeur)


def test_poteau_court_K_C_egal_1():
    # L_(b) = 380 mm : C_C(b) = 10 exactement, K_C(b) = 1,00
    r = _cales(L_selon_b=380, distance_des_connecteurs=15)  # 15 mm <= 380 mm / 20 = 19 mm : A
    assert r.etape("C_{C(b)}").valeur == pytest.approx(10)
    assert r.etape("K_{C(b)}").valeur == 1.00


def test_condition_B():
    r = _cales(distance_des_connecteurs=200)  # entre 150 mm et 300 mm : condition B
    assert r.etape("C_K").valeur == pytest.approx(35.898, abs=1e-3)
    # K_C(b) = 6500 MPa x 3,00 / (1,8 x 78,947² x 11,5 MPa) = 19 500 / 129 017 = 0,15114
    assert r.etape("K_{C(b)}").valeur == pytest.approx(0.15114, abs=1e-4)
    assert any("condition B" in note and "L / 10" in note for note in r.notes)


def test_verification_ratio_au_seuil():
    p_r = _cales().etape("P_r").valeur  # N
    r = _cales(P_f=p_r / 1000)  # kN, ratio = 1,00 exactement
    assert r.verification.ratio == pytest.approx(1.0)
    assert r.verification.respecte


def test_calcul_refuse():
    with pytest.raises(ValueError, match="A.6.5.5.3.1"):
        _cales(nombre_de_pieces=1)
    with pytest.raises(ValueError, match="80"):
        _cales(L_selon_b=3050)  # C_C(b) = 80,26
    with pytest.raises(ValueError, match="50"):
        _cales(L_selon_d=7100)  # C_C(d) d'une pièce = 50,7
    with pytest.raises(ValueError, match="A.6.5.5.3.3"):
        _cales(distance_des_connecteurs=310)  # plus de L / 10 = 300 mm


def test_notes_des_cales():
    r = _cales()
    assert r.notes[0].startswith("Datum ne vérifie pas les cales")
    texte = " ".join(r.notes)
    for article in ("A.6.5.5.3.1", "A.6.5.5.3.2 a)", "A.6.5.5.3.2 b)", "A.6.5.5.3.2 c)", "A.6.5.5.3.3",
                    "A.6.5.5.3.4", "A.6.5.5.3.6"):
        assert article in texte
    # L / 20 = 3000 mm / 20 = 150 mm : connecteurs à 150 mm, condition A
    assert "150 mm" in texte and "condition A" in texte
    assert "13.83 kN" in texte  # 13 832 N
    # Cales de 19 mm (la moitié de 38 mm exactement) : longueur ajustée ; 15 mm : sous la moitié
    assert "longueur de chaque cale doit être augmentée" in " ".join(_cales(epaisseur_des_cales=19).notes)
    assert "ATTENTION" in " ".join(_cales(epaisseur_des_cales=15).notes)
    # Groupe d'essences absent du tableau A.5 : constante non calculée
    sans_groupe = _cales(groupe_d_essences=None)
    assert "non calculée" in " ".join(sans_groupe.notes)
    assert all(not e.description.startswith("Constante") for e in sans_groupe.etapes)


def test_registre_et_figure():
    calcul = registre.calcul("csa_o86_19", "A.6.5.5.3")
    assert calcul.fonction is art.verifier_compression_element_avec_cales_d_espacement
    svg_a = figure(_cales())
    assert svg_a.startswith("<svg") and "L/20" in svg_a and "L/10" not in svg_a
    assert "L/10" in figure(_cales(distance_des_connecteurs=200, nombre_de_pieces=3))
    sans_section = figure(_cales(), avec_section=False)
    assert "viewBox='-20 0 300 236'" in sans_section
