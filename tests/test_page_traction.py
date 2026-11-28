"""
Page Bois de sciage, onglet Traction parallèle au fil (6.5.8) : nouveau moteur seulement.

L'onglet, le Résumé et la note PDF affichent les mêmes T_r. Valeurs attendues calculées à la main
(CSA O86:19, 6.5.8, p. 74) pour un 2x6 S-P-F n° 1/n° 2 (38 mm x 140 mm) :
f_t = 5.5 MPa (tableau 6.4) ; K_Zt = 1.3 (tableau 6.13, grande face de 140 mm) ;
K_D = 1.00 (durée normale), K_St = 1.00 (sec), K_T = 1.00, K_H = 1.00 (1 pli, sans système).
T_r = 0.9 x F_t x A_n x K_Zt, avec A_n = A_g = b d par défaut (aucune réduction, PR #107).
"""

import re

from tests.test_acces import _connecte


def _page(piece="2x6", humide=False, reduction=False, reduction_de_b=None, reduction_de_d=None,
          T_f=None, compte=("admin", "mot-admin")):
    at = _connecte(*compte)
    [t for t in at.text_input if t.key == "piece"][0].set_value(piece).run()
    if humide:
        [c for c in at.checkbox if c.label == "Utilisation en milieu humide"][0].check().run()
    if reduction:
        [t for t in at.toggle if t.key == "trac_reduction"][0].set_value(True).run()
    for cle, texte in (("trac_reduction_b", reduction_de_b), ("trac_reduction_d", reduction_de_d),
                       ("trac_tf", T_f)):
        if texte is not None:
            [n for n in at.text_input if n.key == cle][0].set_value(texte)
    at.run()
    assert not at.exception
    return at


def _T_r(at):
    """T_r affichée dans l'onglet (ex. « $T_r = \\text{34.2 kN (7696 lb)}$ ») : texte et valeur en kN."""
    m = next(m.value for m in at.markdown if m.value.startswith("$T_r = "))
    return m, float(re.search(r"\\text\{([\d.]+) kN", m).group(1))


def _ligne_du_resume(at):
    tableau = next(m.value for m in at.markdown if m.value.startswith("| Article"))
    return next(l for l in tableau.splitlines() if "6.5.8" in l)


def _messages(at):
    return [m.value for m in list(at.success) + list(at.error) + list(at.info)]


def test_sans_reduction():
    """
    A_n = A_g = 38 mm x 140 mm = 5320 mm² ;
    T_r = 0.9 x 5.5 MPa x 5320 mm² x 1.3 = 34 234.2 N -> 34.2 kN ;
    34 234.2 N / 4448.22 N/lb = 7696 lb, affiché avec 3 chiffres significatifs : 7 700 lb ;
    T_f = 10 kN : 10 kN / 34.2342 kN = 29.21 %.
    """
    at = _page(T_f="10 kN")
    texte, t_r = _T_r(at)
    assert t_r == 34.2  # kN
    assert "(7\xa0700 lb)" in texte  # espace insécable entre les milliers
    assert "État limite respecté: 29.21%" in _messages(at)
    # Onglet = Résumé
    ligne = _ligne_du_resume(at)
    assert "$T_r$ = 34.2 kN" in ligne and "$T_f$ = 10.0 kN" in ligne


def test_sans_charge():
    """Sans T_f : T_r est affichée, avec le message pour entrer une charge ; Résumé « Charge manquante »."""
    at = _page()
    assert _T_r(at)[1] == 34.2  # kN
    assert "Spécifiez une charge pour vérifier l'état limite" in _messages(at)
    assert "Charge manquante" in _ligne_du_resume(at)


def test_reduction_de_b_et_de_d():
    """
    Section résiduelle (PR #107) : 4 mm retirés de b et 10 mm de d :
    A_n = (38 - 4) mm x (140 - 10) mm = 34 mm x 130 mm = 4420 mm² ; 4420 / 5320 = 0.831 >= 0.75 ;
    T_r = 0.9 x 5.5 MPa x 4420 mm² x 1.3 = 28 443.3 N -> 28.4 kN.
    """
    at = _page(reduction=True, reduction_de_b="4 mm", reduction_de_d="10 mm", T_f="28.4 kN")
    assert _T_r(at)[1] == 28.4  # kN
    # 28.4 kN / 28.4433 kN = 99.85 %
    assert "État limite respecté: 99.85%" in _messages(at)


def test_reduction_activee_mais_vide():
    """Bascule activée, champs vides : aucune réduction (0 mm), même T_r que sans réduction."""
    at = _page(reduction=True)
    assert _T_r(at)[1] == 34.2  # kN


def test_reduction_refusee_sous_75_pourcent():
    """
    Exemple de la PR #107 : 0.5 po (12.7 mm) retiré de b et de d : 25.3 mm x 127.3 mm = 3220.69 mm²
    < 0.75 x 5320 mm² = 3990 mm² (5.3.8.2) : message d'erreur, aucune T_r, rien dans le Résumé.
    """
    at = _page(reduction=True, reduction_de_b="0.5 po", reduction_de_d="0.5 po", T_f="10 kN")
    assert any("0.75 Ag" in e.value for e in at.error)
    assert not any(m.value.startswith("$T_r = ") for m in at.markdown)
    assert "Non calculé" in _ligne_du_resume(at)


def test_reduction_toute_la_largeur_refusee():
    """38 mm retirés de b = 38 mm : aucune section ; refusé (5.3.8.1)."""
    at = _page(reduction=True, reduction_de_b="38 mm")
    assert any("toute la section" in e.value for e in at.error)


def test_milieu_humide():
    """K_St = 0.84 (tableau 6.10, humide, face étroite <= 89 mm) : 34 234.2 N x 0.84 = 28 756.7 N -> 28.8 kN."""
    at = _page(humide=True)
    assert _T_r(at)[1] == 28.8  # kN


def test_element_compose_K_H_des_poutres_composees():
    """
    2-2x6 : b = 2 x 38 mm = 76 mm (largeur totale, issue #95) ; K_H = 1.00 (tableau 6.12, p. 62 :
    colonne « Poutres composées », ligne « Traction parallèle au fil » = 1,00 ; un élément de 2 plis
    prend toujours cette colonne, issue #7) ; A_n = 76 mm x 140 mm = 10 640 mm² ;
    T_r = 0.9 x 5.5 MPa x 10 640 mm² x 1.3 = 68 468.4 N -> 68.5 kN.
    """
    at = _page(piece="2 2x6")
    assert _T_r(at)[1] == 68.5  # kN


def test_cas_1_sans_plis_K_H_1_10():
    """
    1 pli, « 3 éléments ou + @ <= 2 pi c/c » (cas 1) : K_H = 1.10 (tableau 6.12, traction, cas 1) ;
    T_r = 0.9 x (5.5 MPa x 1.10) x 5320 mm² x 1.3 = 37 657.6 N -> 37.7 kN.
    """
    at = _connecte("admin", "mot-admin")
    [c for c in at.checkbox if c.label == "3 éléments ou + @ ≤ 2 pi c/c"][0].check().run()
    assert not at.exception
    assert _T_r(at)[1] == 37.7  # kN


def test_cas_2_K_H_1_00():
    """
    Cas 2 (revêtement) : « — » au tableau 6.12 pour la traction, donc K_H = 1.00 (issue #7) :
    même T_r que sans système, 34.2 kN.
    """
    at = _connecte("admin", "mot-admin")
    [c for c in at.checkbox if c.label == "Revêtement ou sous-plancher"][0].check().run()
    assert not at.exception
    assert _T_r(at)[1] == 34.2  # kN


def test_lantier_sans_l_onglet_tant_que_non_coche():
    """La case `traction` n'est pas cochée dans ACCES_GROUPE_LANTIER.md : pas d'onglet Traction."""
    at = _connecte("lantier", "mot-lantier")
    assert "Traction parallèle au fil" not in [t.label for t in at.tabs]
