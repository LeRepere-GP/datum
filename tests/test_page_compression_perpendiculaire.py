"""
Page Bois de sciage, onglet Compression perpendiculaire au fil : valeurs du nouveau moteur seulement
(comme l'onglet Cisaillement, issue #98 ; étape 7 de la feuille de route, issue #30).

L'onglet, le Résumé et la note PDF affichent les mêmes Q_r et Q'_r, avec les mêmes chiffres significatifs.
Valeurs attendues calculées à la main (CSA O86:19, 6.5.6) pour 2x6 S-P-F n° 1/n° 2 au sec :
b = 38 mm, d = 140 mm, f_cp = 5.3 MPa (tableau 6.3), K_D = K_Scp = K_T = 1.00,
K_Zcp = 1.00 (largeur / hauteur = 38 mm / 140 mm = 0.27 <= 1.0, tableau 6.15).
"""

import re

from tests.test_acces import _connecte


def _page(plis=1, L_b=None, R_f=None, conditions_appui=False, charge_pres=False, L_b_charge=None,
          P_f=None, densite=False, nlga=False):
    at = _connecte("admin", "mot-admin")
    if plis != 1:
        [t for t in at.text_input if t.key == "piece"][0].set_value(f"{plis} 2x6").run()  # plis de 2x6 (datum-retours #20)
    for cle, coche in (
        ("cp_support_far", conditions_appui), ("cp_support_low_bending", conditions_appui),
        ("cp_near_load", charge_pres), ("cp_use_density", densite),
    ):
        if coche:
            [c for c in at.checkbox if c.key == cle][0].check().run()
    if nlga:
        [c for c in at.checkbox if c.key == "cp_nlga"][0].check().run()
    for cle, texte in (
        ("cp_support_length", L_b), ("cp_rf", R_f), ("cp_load_length", L_b_charge), ("cp_pf", P_f),
    ):
        if texte is not None:
            [n for n in at.text_input if n.key == cle][0].set_value(texte)
    at.run()
    assert not at.exception
    return at


def _affiche(at, symbole):
    """Valeur métrique affichée dans l'onglet (ex. « $Q_r = \\text{14.3 kN (3224 lb)}$ » -> 14.3)."""
    m = next(m.value for m in at.markdown if m.value.startswith(f"${symbole} = "))
    return float(re.search(r"\\text\{([\d.]+) kN", m).group(1))


def _ligne_du_resume(at, article):
    tableau = next(m.value for m in at.markdown if m.value.startswith("| Vérification"))
    return next(ligne for ligne in tableau.splitlines() if article in ligne)


def _messages(at):
    return [m.value for m in list(at.success) + list(at.error) + list(at.info)]


def test_appui_simple():
    """
    L_b = 89 mm, sans les conditions de 6.5.6.5 : K_B = 1.00 ; A_b = 38 mm x 89 mm = 3382 mm² ;
    Q_r = 0.8 x 5.3 MPa x 3382 mm² x 1.00 x 1.00 = 14 339.68 N -> 14.3 kN ;
    R_f = 10 kN : 10 kN / 14.340 kN = 69.74 %.
    """
    at = _page(L_b="89 mm", R_f="10 kN")
    assert _affiche(at, "Q_r") == 14.3  # kN
    assert "État limite respecté: 69.74%" in _messages(at)
    # Onglet = Résumé
    assert "$Q_r$ = 14.3 kN" in _ligne_du_resume(at, "6.5.6.2")


def test_appui_avec_K_B():
    """
    L_b = 38 mm, appui loin de l'extrémité et hors des fortes contraintes de flexion (6.5.6.5 a) et b)) :
    K_B = (38 mm + 9.525 mm) / 38 mm = 1.2507 ; A_b = 38 mm x 38 mm = 1444 mm² ;
    Q_r = 0.8 x 5.3 MPa x 1444 mm² x 1.2507 x 1.00 = 7657.3 N -> 7.66 kN ;
    R_f = 8 kN : 8 kN / 7.6573 kN = 104.48 % (dépassé).
    """
    at = _page(L_b="38 mm", R_f="8 kN", conditions_appui=True)
    assert _affiche(at, "Q_r") == 7.66  # kN
    assert "État limite dépassé: 104.48%" in _messages(at)


def test_charge_pres_de_l_appui():
    """
    6.5.6.3 : L_b = 89 mm à l'appui, 140 mm pour la charge, sans les conditions de 6.5.6.5 (K_B = 1.00).
    L_b1 = 89 mm (la plus petite), L_b2 = 140 mm ;
    A'_b = min(38 mm x (89 mm + 140 mm) / 2 = 4351 mm² ; 1.5 x 38 mm x 89 mm = 5073 mm²) = 4351 mm² ;
    Q'_r = 2/3 x 0.8 x 5.3 MPa x 4351 mm² x 1.00 x 1.00 = 12 298.83 N -> 12.3 kN ;
    P_f = 5 kN : 5 kN / 12.299 kN = 40.65 %.
    """
    at = _page(L_b="89 mm", R_f="10 kN", charge_pres=True, L_b_charge="140 mm", P_f="5 kN")
    assert _affiche(at, "Q'_r") == 12.3  # kN
    assert _affiche(at, "Q_r") == 14.3  # kN, l'appui est toujours vérifié
    messages = _messages(at)
    assert "État limite respecté: 40.65%" in messages
    assert "État limite respecté: 69.74%" in messages
    assert "12.3 kN" in _ligne_du_resume(at, "6.5.6.3")
    # « Voir plus » : détail tiré de la même trace (K_B = min des deux K_B, A'_b, Q'_r)
    detail = next(m.value for m in at.markdown if m.value.startswith("Charge près de l'appui"))
    assert r"K_B = \min(" in detail and "= 1.0000$" in detail
    assert "12.3 kN" in detail


def test_element_compose_de_2_plis():
    """
    2-2x6 : largeur de l'élément = 2 x 38 mm = 76 mm (b par défaut) ; 76 mm / 140 mm = 0.54 -> K_Zcp = 1.00 ;
    Q_r = 0.8 x 5.3 MPa x (76 mm x 89 mm = 6764 mm²) = 28 679.36 N -> 28.7 kN.
    """
    at = _page(plis=2, L_b="89 mm", R_f="10 kN")
    assert _affiche(at, "Q_r") == 28.7  # kN
    assert "État limite respecté: 34.87%" in _messages(at)  # 10 kN / 28.679 kN


def test_f_cp_a_partir_de_la_densite_NLGA():
    """
    A.6.5.6, S-P-F : G = 0.42 (tableau A.11), densité marquée NLGA (sans la limite de tolérance de 0.9) :
    f_cp = 5.8559 MPa > 5.3 MPa (avertissement « non conservateur ») ;
    Q_r = 0.8 x 5.8559 MPa x 3382 mm² = 15 843.7 N -> 15.8 kN.
    """
    at = _page(L_b="89 mm", R_f="10 kN", densite=True, nlga=True)
    assert [n for n in at.number_input if n.key == "cp_density"][0].value == 0.42
    assert _affiche(at, "Q_r") == 15.8  # kN
    assert any("non conservateur" in w.value for w in at.warning)
    assert "État limite respecté: 63.12%" in _messages(at)  # 10 kN / 15.844 kN


def test_sans_longueur_d_appui():
    """Sans L_b : pas de Q_r, message pour entrer la longueur d'appui."""
    at = _page(R_f="10 kN")
    assert not any(m.value.startswith("$Q_r = ") for m in at.markdown)
    assert "Spécifiez la longueur d'appui pour calculer $Q_r$" in _messages(at)


def test_sans_charge():
    """Sans R_f : Q_r affiché, avec le message pour entrer une charge."""
    at = _page(L_b="89 mm")
    assert _affiche(at, "Q_r") == 14.3  # kN
    assert "Spécifiez une charge pour vérifier l'état limite" in _messages(at)
