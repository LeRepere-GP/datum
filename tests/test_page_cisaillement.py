"""
Page Bois de sciage, onglet Cisaillement : valeurs du nouveau moteur seulement (issue #98).

L'onglet, le Résumé et la note PDF affichent les mêmes V_r et F_r, avec les mêmes chiffres significatifs.
Valeurs attendues calculées à la main (CSA O86:19, 6.5.4.3 et 6.5.4.4) pour 2-2x6 S-P-F n° 1/n° 2 :
b = 2 x 38 mm = 76 mm, d = 140 mm, f_v = 1.5 MPa (tableau 6.3), K_Zv = 1.4 (tableau 6.13).
"""

import re

from tests.test_acces import _connecte


def _page(plis=2, humide=False, d_n=None, e=None, V_f=None):
    at = _connecte("admin", "mot-admin")
    [t for t in at.text_input if t.key == "piece"][0].set_value(f"{plis} 2x6").run()  # plis de 2x6 (datum-retours #20)
    if humide:
        [c for c in at.checkbox if c.label == "Utilisation en milieu humide"][0].check().run()
    for cle, texte in (("cis_d_n", d_n), ("cis_e", e), ("cis_vf", V_f)):
        if texte is not None:
            [n for n in at.text_input if n.key == cle][0].set_value(texte)
    at.run()
    assert not at.exception
    return at


def _affiche(at, symbole):
    """Valeur métrique affichée dans l'onglet (ex. « $F_r = \\text{2.27 kN (510 lb)}$ » -> 2.27)."""
    m = next(m.value for m in at.markdown if m.value.startswith(f"${symbole} = "))
    return m, float(re.search(r"\\text\{([\d.]+) kN", m).group(1))


def _ligne_du_resume(at, article):
    tableau = next(m.value for m in at.markdown if m.value.startswith("| Vérification"))
    return next(l for l in tableau.splitlines() if article in l)


def _messages(at):
    return [m.value for m in list(at.success) + list(at.error) + list(at.info)]


def test_fissuration_avec_K_H_de_autre_propriete():
    """
    Scénario de l'issue #98 : milieu humide, d_n = 30 mm, e = 200 mm, V_f = 4 kN.
    F_r : F_f = 0.50 MPa x (1.00 x 1.00 x 0.70 x 1.00) = 0.35 MPa (K_H « Autre propriété » = 1.00,
    K_Sf = 0.70) ; alpha = 110 mm / 140 mm = 0.7857 ; eta = 200 mm / 140 mm = 1.4286 ; K_N = 0.6763 ;
    F_r = 0.9 x 0.35 MPa x 10 640 mm² x 0.6763 = 2267 N -> 2.27 kN (510 lb) ; 4 kN / 2.267 kN = 176.47 %.
    V_r : F_v = 1.5 MPa x 1.10 x 0.96 = 1.584 MPa (K_H des poutres composées, K_Sv = 0.96) ;
    A_n = 76 mm x 110 mm = 8360 mm² ; V_r = 0.9 x 1.584 MPa x 2/3 x 8360 mm² x 1.4 = 11 123 N -> 11.1 kN ;
    4 kN / 11.123 kN = 35.96 %.
    """
    at = _page(humide=True, d_n="30 mm", e="200 mm", V_f="4 kN")
    texte_f_r, f_r = _affiche(at, "F_r")
    assert f_r == 2.27  # kN, et non 2.49 kN (ancien module, K_H = 1.10)
    assert "(510 lb)" in texte_f_r
    _, v_r = _affiche(at, "V_r")
    assert v_r == 11.1  # kN
    messages = _messages(at)
    assert "État limite dépassé: 176.47%" in messages
    assert "État limite respecté: 35.96%" in messages
    # Onglet = Résumé
    assert "$F_r$ = 2.27 kN" in _ligne_du_resume(at, "6.5.4.4")
    assert "$V_r$ = 11.1 kN" in _ligne_du_resume(at, "6.5.4.3")


def test_les_deux_verifications_avec_une_entaille():
    """
    Au sec, d_n = 10 mm, e = 50 mm : F_r = 13 276 N -> 13.3 kN gouverne, V_r = 13 694 N -> 13.7 kN.
    L'onglet montre les deux, au lieu du minimum seulement (ancien affichage : V_r = 13.69 kN seul).
    """
    at = _page(d_n="10 mm", e="50 mm", V_f="10 kN")
    assert _affiche(at, "F_r")[1] == 13.3  # kN
    assert _affiche(at, "V_r")[1] == 13.7  # kN
    messages = _messages(at)
    assert "État limite respecté: 75.32%" in messages  # 10 kN / 13.276 kN
    assert "État limite respecté: 73.03%" in messages  # 10 kN / 13.694 kN


def test_sans_entaille_V_r_seulement():
    """1 pli, au sec : V_r = 0.9 x 1.5 MPa x 1.00 x 2/3 x 5320 mm² x 1.4 = 6703 N -> 6.70 kN (K_H = 1.00)."""
    at = _page(plis=1, V_f="1 kN")
    assert _affiche(at, "V_r")[1] == 6.70  # kN
    assert not any(m.value.startswith("$F_r = ") for m in at.markdown)
    assert "État limite respecté: 14.92%" in _messages(at)  # 1 kN / 6.703 kN


def test_entaille_sans_charge():
    """Sans V_f : les résistances sont affichées, avec le message pour entrer une charge."""
    at = _page(d_n="30 mm", e="200 mm")
    assert _affiche(at, "F_r")[1] > 0
    assert _messages(at).count("Spécifiez une charge pour vérifier l'état limite") >= 2


def test_entaille_incomplete_pas_de_fissuration():
    """d_n sans e : pas de cisaillement par fissuration (6.5.4.4 demande d_n et e)."""
    at = _page(d_n="30 mm", V_f="1 kN")
    assert not any(m.value.startswith("$F_r = ") for m in at.markdown)
