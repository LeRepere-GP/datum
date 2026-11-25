"""Tests de 6.5.8 Résistance à la traction parallèle au fil (CSA O86:19, p. 74)."""

import pytest

from moteur.commun import registre
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_3_resistances_prevues_et_modules_d_elasticite import (  # noqa: E501
    resistances_prevues,
)
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_4_coefficients_de_correction import (
    POUTRES_COMPOSEES,
    TRACTION_PARALLELE,
    K_H,
    K_S,
    K_Z,
)
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances.art_6_5_8_resistance_a_la_traction_parallele_au_fil import (  # noqa: E501
    F_t,
    T_r,
    verifier_traction,
)


# --- Fonctions simples

def test_F_t():
    assert F_t(5.5) == 5.5
    # 5.5 MPa x (1.15 x 1.1 x 0.84 x 0.85) = 5.5 MPa x 0.903210 = 4.967655 MPa
    assert F_t(5.5, 1.15, 1.1, 0.84, 0.85) == pytest.approx(4.967655)


def test_T_r():
    # 0.9 x 5.5 MPa x 5320 mm² x 1.3 = 34 234.2 N
    assert T_r(5.5, 5320, 1.3) == pytest.approx(34234.2)
    # Sans K_Zt : 0.9 x 5.5 MPa x 5320 mm² = 26 334 N
    assert T_r(5.5, 5320) == pytest.approx(26334.0)


# --- Vérification

def _etape(r, symbole):
    return r.etape(symbole).valeur


def _donnee(r, symbole):
    return next(d.valeur for d in r.donnees if d.symbole == symbole)


def test_verifier_traction_sans_reduction():
    # 38 x 140 mm, S-P-F n° 1/n° 2 : f_t = 5.5 MPa (tableau 6.4, p. 51), K_Zt = 1.3 (tableau 6.13)
    r = verifier_traction(b=38, d=140, f_t=5.5, K_Zt=1.3)
    assert r.article == "6.5.8" and r.figure == "traction"
    assert _etape(r, "F_t") == pytest.approx(5.5)
    assert _etape(r, "A_g") == pytest.approx(5320)  # 38 mm x 140 mm = 5320 mm²
    assert _etape(r, "A_n") == pytest.approx(5320)  # aucune réduction : A_n = A_g
    assert _etape(r, "T_r") == pytest.approx(34234.2)  # 0.9 x 5.5 MPa x 5320 mm² x 1.3 = 34 234.2 N
    assert r.verification is None  # sans T_f


def test_verifier_traction_avec_section_nette():
    # A_n = 4500 mm² (ex. trou de boulon) : 4500 / 5320 = 0.84586 >= 0.75 (5.3.8.2)
    r = verifier_traction(b=38, d=140, f_t=5.5, A_n=4500, K_Zt=1.3)
    assert _donnee(r, "A_n") == 4500
    assert _etape(r, "T_r") == pytest.approx(28957.5)  # 0.9 x 5.5 MPa x 4500 mm² x 1.3 = 28 957.5 N
    rapport = [e for e in r.etapes if e.article == "5.3.8.2"]
    assert len(rapport) == 1 and rapport[0].symbole == ""  # pas de symbole dans la norme
    assert rapport[0].valeur == pytest.approx(4500 / 5320)


def test_verifier_traction_section_nette_au_seuil():
    # A_n = 0.75 x 5320 mm² = 3990 mm² : accepté ; 0.9 x 5.5 MPa x 3990 mm² x 1.3 = 25 675.65 N
    r = verifier_traction(b=38, d=140, f_t=5.5, A_n=3990, K_Zt=1.3)
    assert _etape(r, "T_r") == pytest.approx(25675.65)


@pytest.mark.parametrize("a_n", [3989.9, 0, 5321])
def test_verifier_traction_section_nette_refusee(a_n):
    # 3989.9 mm² < 0.75 A_g ; 0 mm² ; 5321 mm² > A_g = 5320 mm²
    with pytest.raises(ValueError):
        verifier_traction(b=38, d=140, f_t=5.5, A_n=a_n)


def test_verifier_traction_coefficients():
    r = verifier_traction(b=38, d=140, f_t=5.5, K_D=1.15, K_H=1.1, K_St=0.84, K_T=0.85, K_Zt=1.3)
    assert _etape(r, "F_t") == pytest.approx(4.967655)
    # 0.9 x 4.967655 MPa x 5320 mm² x 1.3 = 30 920.6 N
    assert _etape(r, "T_r") == pytest.approx(0.9 * 4.967655 * 5320 * 1.3)
    assert _etape(r, "T_r") == pytest.approx(30920.6, rel=1e-5)


def test_verifier_traction_ratio():
    # T_f = 20 kN : 20 kN / 34.2342 kN = 58.42 %
    r = verifier_traction(b=38, d=140, f_t=5.5, K_Zt=1.3, T_f=20)
    assert r.verification.ratio == pytest.approx(20 / 34.2342)
    assert r.verification.symbole_charge == "T_f" and r.verification.symbole_resistance == "T_r"
    assert r.verification.unite == "kN"


def test_verifier_traction_ratio_egal_a_1():
    # T_f = T_r = 34.2342 kN : ratio = 1.00 exactement, état limite respecté
    r = verifier_traction(b=38, d=140, f_t=5.5, K_Zt=1.3, T_f=34.2342)
    assert r.verification.ratio == pytest.approx(1.0)
    assert r.verification.respecte


def test_verifier_traction_ratio_depasse():
    r = verifier_traction(b=38, d=140, f_t=5.5, K_Zt=1.3, T_f=35)  # 35 kN / 34.2342 kN = 1.0224
    assert not r.verification.respecte


def test_verifier_traction_element_compose():
    # 2 plis de 38 mm : b = 76 mm (largeur de l'élément, issue #95) ; largeur d'un pli 38 mm
    r = verifier_traction(b=76, d=140, f_t=5.5, plis=2, K_Zt=1.3)
    assert _donnee(r, "b") == 76
    pli = [d for d in r.donnees if d.description == "Largeur d'un pli"]
    assert len(pli) == 1 and pli[0].valeur == 38 and pli[0].symbole == ""
    assert _etape(r, "A_g") == pytest.approx(10640)  # 76 mm x 140 mm = 10 640 mm²
    assert _etape(r, "T_r") == pytest.approx(68468.4)  # 0.9 x 5.5 MPa x 10 640 mm² x 1.3 = 68 468.4 N


def test_verifier_traction_un_pli_sans_largeur_de_pli():
    r = verifier_traction(b=38, d=140, f_t=5.5)
    assert not [d for d in r.donnees if d.description == "Largeur d'un pli"]


def test_chaine_complete_avec_les_tableaux():
    """
    S-P-F n° 1/n° 2, 2 plis de 38 x 140 mm, milieu humide, durée normale :
    f_t = 5.5 MPa (tableau 6.4) ; K_St = 0.84 (tableau 6.10, humide, face étroite <= 89 mm) ;
    K_H = 1.00 (tableau 6.12, poutres composées, traction, p. 62) ; K_Zt = 1.3 (tableau 6.13, 140 mm).
    F_t = 5.5 MPa x (1.0 x 1.00 x 0.84 x 1.0) = 4.62 MPa
    T_r = 0.9 x 4.62 MPa x (76 mm x 140 mm = 10 640 mm²) x 1.3 = 57 513.456 N
    """
    f_t = resistances_prevues("Lumber", "spf", "n1-n2").f_t
    k_st = K_S(TRACTION_PARALLELE, milieu_humide=True, face_etroite=76)
    k_h = K_H(TRACTION_PARALLELE, POUTRES_COMPOSEES)
    k_zt = K_Z(TRACTION_PARALLELE, 76, 140, "Lumber")
    assert (f_t, k_st, k_h, k_zt) == (5.5, 0.84, 1.00, 1.3)
    r = verifier_traction(b=76, d=140, f_t=f_t, plis=2, K_H=k_h, K_St=k_st, K_Zt=k_zt)
    assert _etape(r, "F_t") == pytest.approx(4.62)
    assert _etape(r, "T_r") == pytest.approx(57513.456)


def test_enregistree_dans_le_catalogue():
    c = registre.calcul("csa_o86_19", "6.5.8")
    assert c.fonction is verifier_traction
    assert c.titre == "Résistance à la traction parallèle au fil"
