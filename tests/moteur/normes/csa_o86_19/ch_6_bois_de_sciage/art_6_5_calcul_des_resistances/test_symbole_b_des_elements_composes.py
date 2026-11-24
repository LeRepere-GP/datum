"""
Issue #95 : b = « largeur de l'élément, mm » (3.2, p. 35), tous les plis compris. La largeur d'un pli
(« élément individuel », 6.5.3.2.4, p. 65) n'a pas de symbole dans la norme. Aucun résultat ne change.
"""

import pytest

from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_3_resistance_au_moment_de_flexion as art_6_5_3,
    art_6_5_4_resistance_au_cisaillement as art_6_5_4,
)

# 2 plis de 38 mm : b = 2 x 38 mm = 76 mm. Flexion : d = 184 mm (d/b = 184 mm / 76 mm = 2.42 <= 2.5,
# 6.5.3.2.4 ; un pli : 184 mm / 38 mm = 4.84 <= 6.5, rive comprimée maintenue, 6.5.3.2.3 c)) ;
# cisaillement : d = 235 mm
VERIFICATIONS = {
    "flexion": lambda plis, b: art_6_5_3.verifier_flexion(
        b, 184, 11.8, plis=plis, plis_fixes_a_au_plus_4d=True, support_lateral_aux_appuis=True,
        rive_comprimee_maintenue=True,
    ),
    "cisaillement": lambda plis, b: art_6_5_4.verifier_cisaillement(b, 235, 1.5, plis=plis, d_n=20),
    "fissuration": lambda plis, b: art_6_5_4.verifier_cisaillement_par_fissuration(
        b, 235, 20, 100, plis=plis
    ),
}


def _donnees(r):
    return {(d.symbole, d.description): d.valeur for d in r.donnees}


@pytest.mark.parametrize("nom", VERIFICATIONS)
def test_b_est_la_largeur_de_l_element(nom):
    donnees = _donnees(VERIFICATIONS[nom](2, 76))
    assert donnees[("b", "Largeur de l'élément")] == 76  # mm
    assert donnees[("", "Largeur d'un pli")] == 38  # 76 mm / 2 = 38 mm, sans symbole
    assert donnees[("", "Nombre de plis")] == 2
    assert all(symbole != "b" or valeur == 76 for (symbole, _), valeur in donnees.items())


@pytest.mark.parametrize("nom", VERIFICATIONS)
def test_un_pli_sans_largeur_d_un_pli(nom):
    donnees = _donnees(VERIFICATIONS[nom](1, 38))
    assert donnees[("b", "Largeur de l'élément")] == 38  # mm
    assert ("", "Largeur d'un pli") not in donnees


@pytest.mark.parametrize("nom", VERIFICATIONS)
def test_formules_sans_n(nom):
    """Le symbole n (nombre de plis) n'existe pas dans la norme (3.2 n'a que n_F) : b suffit."""
    r = VERIFICATIONS[nom](2, 76)
    for etape in r.etapes:
        assert r"n \," not in etape.formule, (nom, etape.symbole)
        assert r"n b" not in etape.formule, (nom, etape.symbole)


def test_substitutions_avec_la_largeur_totale():
    flexion = VERIFICATIONS["flexion"](2, 76)
    # S = b d² / 6 = 76 mm x (184 mm)² / 6 = 428 842.7 mm³
    assert flexion.etape("S").valeur == pytest.approx(428_842.67, abs=0.01)
    assert flexion.etape("S").formule == r"S = \frac{b \, d^2}{6}"
    assert "76.0 \\times" in flexion.etape("S").substitution and r"2 \times" not in flexion.etape("S").substitution
    # K_L : d/b = 184 mm / 76 mm = 2.42 <= 2.5, substitution avec la largeur totale
    assert r"\frac{184}{76.0}" in flexion.etape("K_L").substitution  # 3 chiffres significatifs
    assert flexion.etape("K_L").valeur == 1.0
    cisaillement = VERIFICATIONS["cisaillement"](2, 76)
    # A_n = b (d - d_n) = 76 mm x (235 mm - 20 mm) = 16 340 mm²
    assert cisaillement.etape("A_n").valeur == 16_340
    assert cisaillement.etape("A_n").formule == r"A_n = b \, (d - d_n)"
    fissuration = VERIFICATIONS["fissuration"](2, 76)
    # A_g = b d = 76 mm x 235 mm = 17 860 mm²
    assert fissuration.etape("A_g").valeur == 17_860
    assert fissuration.etape("A_g").formule == r"A_g = b \, d"


def test_resultats_inchanges():
    """Mêmes résistances qu'avant l'issue #95 (alors b = 38 mm et plis = 2 donnaient 76 mm)."""
    # V_r = 0.9 x 1.5 MPa x (2 x 16 340 mm² / 3) = 14 706 N
    assert VERIFICATIONS["cisaillement"](2, 76).etape("V_r").valeur == pytest.approx(14_706)
    # 3 plis de 38 x 235 mm : b = 114 mm, M_r = 0.9 x 11.8 MPa x (114 mm x (235 mm)² / 6)
    # = 0.9 x 11.8 MPa x 1 049 275 mm³ = 11 143 300.5 N·mm
    r = art_6_5_3.verifier_flexion(114, 235, 11.8, plis=3, plis_fixes_a_au_plus_4d=True)
    assert r.etape("M_r").valeur == pytest.approx(11_143_300.5)
