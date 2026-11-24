"""
Page Bois de sciage : bascules métrique / impérial des dimensions et des charges (retour
LeRepere-GP/datum-retours#10, PR #99, interface_unites.py).

Les calculs restent en métrique : les bascules ne changent que l'affichage des entrées et des résultats.
1 po = 25.4 mm ; 1 pi = 304.8 mm ; 1 lb = 4.4482216 N (moteur/commun/unites.py).
"""

from tests.test_acces import _connecte

DIMENSIONS, CHARGES = "unites_dimensions", "unites_charges"


def _basculer(at, cle, systeme):
    [b for b in at.sidebar.get("button_group") if b.key == cle][0].set_value(systeme).run()
    assert not at.exception
    return at


def _champ(at, debut):
    return [n for n in at.number_input if n.label.startswith(debut)][0]


def _texte(at, debut):
    return [t for t in at.text_input if t.label.startswith(debut)][0]


def _qr(at):
    return [m.value for m in at.markdown if m.value.startswith("$Qr")]


def test_metrique_par_defaut():
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    for cle in (DIMENSIONS, CHARGES):
        assert [b for b in at.sidebar.get("button_group") if b.key == cle][0].value == "Métrique"
    libelles = [n.label for n in at.number_input]
    assert "Longueur d'appui, $L_b$ (mm)" in libelles
    assert "$Rf: (kN)$" in libelles
    assert "$Mf: (kN \\cdot m)$" in libelles
    assert "Longueur de l'élément, $L$ (mm)" in libelles
    # 2x6 : 38 mm x 140 mm (tableau A.3)
    assert [m.value for m in at.metric] == ["38 mm", "140 mm"]


def test_bascules_independantes():
    """Dimensions en impérial et charges en kN (exemple de l'utilisateur), puis l'inverse."""
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Impérial")
    libelles = [n.label for n in at.number_input]
    assert "Longueur d'appui, $L_b$ (po)" in libelles
    assert "$Rf: (kN)$" in libelles
    assert "$Mf: (kN \\cdot m)$" in libelles
    # Longueurs en pieds-pouces (champ texte)
    assert _texte(at, "Longueur de l'élément").label == "Longueur de l'élément, $L$ (pi-po)"
    # 38 mm / 25.4 mm/po = 1.50 po ; 140 mm / 25.4 mm/po = 5.51 po
    assert [m.value for m in at.metric] == ["1.50 po", "5.51 po"]
    # Les dimensions nominales restent en po (« 2x6 »)
    assert [s for s in at.selectbox if s.label.startswith("Largeur nominale")][0].value == 2

    _basculer(at, DIMENSIONS, "Métrique")
    _basculer(at, CHARGES, "Impérial")
    libelles = [n.label for n in at.number_input]
    assert "Longueur d'appui, $L_b$ (mm)" in libelles
    assert "$Rf: (lb)$" in libelles
    assert "$Mf: (lb \\cdot po)$" in libelles  # lb·po, préférence de l'utilisateur (unites.py)


def test_imperial_element_compose():
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Élément composé")][0].set_value(2).run()
    _basculer(at, DIMENSIONS, "Impérial")
    # 2 x 1.50 po = 2.99 po (76 mm / 25.4 mm/po = 2.992 po)
    assert at.metric[0].value == "2*1.50 = 2.99 po"


def test_calcul_en_imperial():
    """
    Entrées en impérial, calcul en métrique, résultat en impérial. 2x6 S-P-F n° 1/n° 2 :
    f_cp = 5.3 MPa, K_D = K_Scp = K_T = K_B = K_Zcp = 1.00 (voir tests/test_page_k_d.py).
    L_b = 3.5 po x 25.4 mm/po = 88.9 mm ; A_b = 38 mm x 88.9 mm = 3378.2 mm²
    Q_r = 0.8 x 5.3 MPa x 3378.2 mm² = 14 323.6 N ; 14 323.6 N / 4.4482 N/lb = 3220 lb
    """
    at = _connecte("admin", "mot-admin")
    _basculer(at, DIMENSIONS, "Impérial")
    _basculer(at, CHARGES, "Impérial")
    _champ(at, "Longueur d'appui").set_value(3.5).run()  # po
    _champ(at, "$Rf").set_value(1000.0).run()  # lb = 4.45 kN
    assert not at.exception
    assert _qr(at) == ["$Qr = 3220 lb$"]
    # Charges en métrique : 14 323.6 N = 14.32 kN (L_b reste 88.9 mm)
    _basculer(at, CHARGES, "Métrique")
    assert _qr(at) == ["$Qr = 14.32 kN$"]


def test_aller_retour_sans_erreur_d_arrondi():
    """89 mm -> 3.50 po (affiché) -> 89 mm : la valeur métrique reste exacte si on ne la change pas."""
    at = _connecte("admin", "mot-admin")
    _champ(at, "Longueur d'appui").set_value(89.0).run()  # mm
    _champ(at, "$Rf").set_value(5.0).run()  # kN
    # Q_r = 0.8 x 5.3 MPa x (38 mm x 89 mm) = 14 340 N = 14.34 kN
    assert _qr(at) == ["$Qr = 14.34 kN$"]
    _basculer(at, DIMENSIONS, "Impérial")
    _basculer(at, CHARGES, "Impérial")
    assert _champ(at, "Longueur d'appui").value == 3.5  # 89 mm / 25.4 mm/po = 3.504 po
    assert _champ(at, "$Rf").value == 1124.0  # 5 000 N / 4.4482 N/lb = 1124 lb
    # 14 340 N / 4.4482 N/lb = 3224 lb : calcul avec 89 mm exactement, pas 3.50 po = 88.9 mm
    assert _qr(at) == ["$Qr = 3224 lb$"]
    _basculer(at, DIMENSIONS, "Métrique")
    _basculer(at, CHARGES, "Métrique")
    assert _champ(at, "Longueur d'appui").value == 89.0
    assert _qr(at) == ["$Qr = 14.34 kN$"]


def test_methode_de_travail_bascules_en_tout_temps():
    """
    Exemple de l'utilisateur : longueur d'appui en po, entaille en mm, largeur d'appui en po, puis
    vérification en mm ; aucune valeur n'est perdue.
    L_b = 3.5 po = 88.9 mm ; d_n = 20 mm ; b = 1.25 po = 31.75 mm.
    Q_r = 0.8 x 5.3 MPa x (31.75 mm x 88.9 mm) = 0.8 x 5.3 MPa x 2822.6 mm² = 11 967.7 N = 11.97 kN
    """
    at = _connecte("admin", "mot-admin")
    _champ(at, "$Rf").set_value(5.0).run()  # kN
    _basculer(at, DIMENSIONS, "Impérial")
    _champ(at, "Longueur d'appui").set_value(3.5).run()  # po
    _basculer(at, DIMENSIONS, "Métrique")
    _champ(at, "Profondeur de l'entaille").set_value(20.0).run()  # mm
    _basculer(at, DIMENSIONS, "Impérial")
    assert _champ(at, "Longueur d'appui").value == 3.5
    assert _champ(at, "Profondeur de l'entaille").value == 0.79  # 20 mm / 25.4 mm/po = 0.787 po
    _champ(at, "Largeur d'appui").set_value(1.25).run()  # po
    _basculer(at, DIMENSIONS, "Métrique")
    assert not at.exception
    assert _champ(at, "Longueur d'appui").value == 89.0  # 88.9 mm, affiché au mm près
    assert _champ(at, "Profondeur de l'entaille").value == 20.0
    assert _champ(at, "Largeur d'appui").value == 32.0  # 31.75 mm, affiché au mm près
    assert _qr(at) == ["$Qr = 11.97 kN$"]


def test_longueur_en_pieds_et_pouces():
    """
    L = 8 pi 6 po = 8.5 pi x 304.8 mm/pi = 2590.8 mm ; affichée 2591 mm en métrique, et de nouveau
    « 8 pi - 6 po » en impérial (valeur gardée exacte).
    """
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Impérial")
    _texte(at, "Longueur de l'élément").set_value("8-6").run()
    _texte(at, "Entraxe des appuis latéraux, flambage selon $b$").set_value("4' 3\"").run()
    assert not at.exception
    _basculer(at, DIMENSIONS, "Métrique")
    assert _champ(at, "Longueur de l'élément").value == 2591.0  # 2590.8 mm
    assert _champ(at, "Entraxe des appuis latéraux, flambage selon $b$").value == 1295.0  # 1295.4 mm
    _basculer(at, DIMENSIONS, "Impérial")
    assert _texte(at, "Longueur de l'élément").value == "8 pi - 6 po"
    assert _texte(at, "Entraxe des appuis latéraux, flambage selon $b$").value == "4 pi - 3 po"


def test_longueur_illisible():
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Impérial")
    _texte(at, "Longueur de l'élément").set_value("huit pieds").run()
    assert not at.exception
    assert any("Longueur illisible" in e.value for e in at.error)


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
    _basculer(at, DIMENSIONS, "Impérial")
    assert _champ(at, "Profondeur de l'entaille").max == 1.37
    assert _champ(at, "Profondeur de l'entaille").value == 1.37
    assert "0.25 \\cdot d = 1.38$ po" in _champ(at, "Profondeur de l'entaille").help
    _basculer(at, DIMENSIONS, "Métrique")
    assert _champ(at, "Profondeur de l'entaille").value == 35.0
    assert [m.value for m in at.markdown if m.value.startswith("$Fr")] == fr_metrique


def test_resume_en_imperial():
    """Tableau « Résumé » selon la bascule des charges ; 1 kN = 224.8 lb -> « 225 lb » (3 chiffres)."""
    at = _connecte("admin", "mot-admin")
    _champ(at, "$Vf").set_value(1.0).run()  # kN
    _basculer(at, CHARGES, "Impérial")
    (tableau,) = [m.value for m in at.markdown if m.value.startswith("| Vérification")]
    ligne = tableau.splitlines()[2]
    assert "$V_f$ = 225 lb" in ligne and "kN" not in ligne


def test_k_d_unite_de_pression():
    """K_D (5.3.2.2) : seul le rapport P_L / P_s compte ; l'unité affichée suit la bascule des charges."""
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Durée")][0].set_value("Continue (permanente)").run()
    [c for c in at.checkbox if c.key == "kd_charges"][0].check().run()
    assert any(n.label == "$P_L$ (kPa)" for n in at.number_input)
    _basculer(at, CHARGES, "Impérial")
    assert any(n.label == "$P_L$ (lb/pi²)" for n in at.number_input)


def test_fractions_de_pouce():
    """
    Exemple de l'utilisateur : 3 pi 2-1/4 po = 38.25 po x 25.4 mm/po = 971.55 mm, affiché 972 mm en
    métrique, puis « 3 pi - 2-1/4 po » en impérial.
    """
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Impérial")
    _texte(at, "Longueur de l'élément").set_value("3 pi 2-1/4 po").run()
    assert not at.exception and not at.error
    _basculer(at, DIMENSIONS, "Métrique")
    assert _champ(at, "Longueur de l'élément").value == 972.0  # 971.55 mm
    _basculer(at, DIMENSIONS, "Impérial")
    assert _texte(at, "Longueur de l'élément").value == "3 pi - 2-1/4 po"
