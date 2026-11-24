"""
Page Bois de sciage : bascule métrique / impérial (retour LeRepere-GP/datum-retours#10, interface_unites.py).

Les calculs restent en métrique : la bascule ne change que l'affichage des entrées et des résultats.
1 po = 25.4 mm ; 1 pi = 304.8 mm ; 1 lb = 4.4482216 N (moteur/commun/unites.py).
"""

from tests.test_acces import _connecte


def _basculer(at, systeme):
    [b for b in at.sidebar.get("button_group") if b.key == "unites"][0].set_value(systeme).run()
    assert not at.exception
    return at


def _champ(at, debut):
    return [n for n in at.number_input if n.label.startswith(debut)][0]


def _qr(at):
    return [m.value for m in at.markdown if m.value.startswith("$Qr")]


def test_metrique_par_defaut():
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    assert [b for b in at.sidebar.get("button_group") if b.key == "unites"][0].value == "Métrique"
    libelles = [n.label for n in at.number_input]
    assert "Longueur d'appui, $L_b$ (mm)" in libelles
    assert "$Rf: (kN)$" in libelles
    assert "$Mf: (kN \\cdot m)$" in libelles
    assert "Longueur de l'élément, $L$ (mm)" in libelles
    # 2x6 : 38 mm x 140 mm (tableau A.3)
    assert [m.value for m in at.metric] == ["38 mm", "140 mm"]


def test_imperial_libelles_et_dimensions():
    at = _basculer(_connecte("admin", "mot-admin"), "Impérial")
    libelles = [n.label for n in at.number_input]
    assert "Longueur d'appui, $L_b$ (po)" in libelles
    assert "$Rf: (lb)$" in libelles
    assert "$Mf: (lb \\cdot po)$" in libelles  # lb·po, préférence de l'utilisateur (unites.py)
    assert "Longueur de l'élément, $L$ (pi)" in libelles
    # 38 mm / 25.4 mm/po = 1.50 po ; 140 mm / 25.4 mm/po = 5.51 po
    assert [m.value for m in at.metric] == ["1.50 po", "5.51 po"]
    # Les dimensions nominales restent en po (« 2x6 ») dans les deux systèmes
    assert [s for s in at.selectbox if s.label.startswith("Largeur nominale")][0].value == 2


def test_imperial_element_compose():
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Élément composé")][0].set_value(2).run()
    _basculer(at, "Impérial")
    # 2 x 1.50 po = 2.99 po (76 mm / 25.4 mm/po = 2.992 po)
    assert at.metric[0].value == "2*1.50 = 2.99 po"


def test_calcul_en_imperial():
    """
    Entrées en impérial, calcul en métrique, résultat en impérial. 2x6 S-P-F n° 1/n° 2 :
    f_cp = 5.3 MPa, K_D = K_Scp = K_T = K_B = K_Zcp = 1.00 (voir tests/test_page_k_d.py).
    L_b = 3.5 po x 25.4 mm/po = 88.9 mm ; A_b = 38 mm x 88.9 mm = 3378.2 mm²
    Q_r = 0.8 x 5.3 MPa x 3378.2 mm² = 14 323.6 N ; 14 323.6 N / 4.4482 N/lb = 3220 lb
    """
    at = _basculer(_connecte("admin", "mot-admin"), "Impérial")
    _champ(at, "Longueur d'appui").set_value(3.5).run()  # po
    _champ(at, "$Rf").set_value(1000.0).run()  # lb = 4.45 kN
    assert not at.exception
    assert _qr(at) == ["$Qr = 3220 lb$"]
    # Même calcul en métrique : 14 323.6 N = 14.32 kN
    _basculer(at, "Métrique")
    assert _qr(at) == ["$Qr = 14.32 kN$"]


def test_aller_retour_sans_erreur_d_arrondi():
    """89 mm -> 3.50 po (affiché) -> 89 mm : la valeur métrique reste exacte si on ne la change pas."""
    at = _connecte("admin", "mot-admin")
    _champ(at, "Longueur d'appui").set_value(89.0).run()  # mm
    _champ(at, "$Rf").set_value(5.0).run()  # kN
    # Q_r = 0.8 x 5.3 MPa x (38 mm x 89 mm) = 14 340 N = 14.34 kN
    assert _qr(at) == ["$Qr = 14.34 kN$"]
    _basculer(at, "Impérial")
    assert _champ(at, "Longueur d'appui").value == 3.5  # 89 mm / 25.4 mm/po = 3.504 po
    assert _champ(at, "$Rf").value == 1124.0  # 5 000 N / 4.4482 N/lb = 1124 lb
    # 14 340 N / 4.4482 N/lb = 3224 lb : calcul avec 89 mm exactement, pas 3.50 po = 88.9 mm
    assert _qr(at) == ["$Qr = 3224 lb$"]
    _basculer(at, "Métrique")
    assert _champ(at, "Longueur d'appui").value == 89.0
    assert _qr(at) == ["$Qr = 14.34 kN$"]


def test_entaille_a_la_limite_en_imperial():
    """
    d_n = 0.25 d = 0.25 x 140 mm = 35 mm (6.5.4.4.2) : en impérial, 35 mm / 25.4 mm/po = 1.378 po ;
    la borne affichée est arrondie vers le bas (1.37 po) et la valeur métrique reste 35 mm exactement
    (la réduire ne serait pas conservateur).
    """
    at = _connecte("admin", "mot-admin")
    _champ(at, "Profondeur de l'entaille").set_value(35.0).run()  # mm
    _champ(at, "Longueur de l'entaille").set_value(100.0).run()  # mm
    _champ(at, "$Vf").set_value(1.0).run()  # kN
    fr_metrique = [m.value for m in at.markdown if m.value.startswith("$Fr")]
    _basculer(at, "Impérial")
    assert _champ(at, "Profondeur de l'entaille").max == 1.37
    assert _champ(at, "Profondeur de l'entaille").value == 1.37
    assert "0.25 \\cdot d = 1.38$ po" in _champ(at, "Profondeur de l'entaille").help
    _basculer(at, "Métrique")
    assert _champ(at, "Profondeur de l'entaille").value == 35.0
    assert [m.value for m in at.markdown if m.value.startswith("$Fr")] == fr_metrique


def test_resume_en_imperial():
    """Tableau « Résumé » dans le système choisi ; 1 kN = 224.8 lb -> « 225 lb » (3 chiffres)."""
    at = _connecte("admin", "mot-admin")
    _champ(at, "$Vf").set_value(1.0).run()  # kN
    _basculer(at, "Impérial")
    (tableau,) = [m.value for m in at.markdown if m.value.startswith("| Vérification")]
    ligne = tableau.splitlines()[2]
    assert "$V_f$ = 225 lb" in ligne and "kN" not in ligne


def test_k_d_unite_de_pression():
    """K_D (5.3.2.2) : seul le rapport P_L / P_s compte ; l'unité affichée suit la bascule."""
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Durée")][0].set_value("Continue (permanente)").run()
    [c for c in at.checkbox if c.key == "kd_charges"][0].check().run()
    assert any(n.label == "$P_L$ (kPa)" for n in at.number_input)
    _basculer(at, "Impérial")
    assert any(n.label == "$P_L$ (lb/pi²)" for n in at.number_input)
