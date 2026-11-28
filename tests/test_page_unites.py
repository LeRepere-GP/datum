"""
Page Bois de sciage : saisie libre des unités et résultats dans les deux unités (retour
LeRepere-GP/datum-retours#10, PR #99, interface_unites.py).

Chaque champ accepte n'importe quelle unité (même mélangées) ; un nombre sans unité prend l'unité par
défaut (deux bascules : dimensions, en impérial au départ, et charges, en métrique au départ). Les calculs
restent en métrique. Les espaces insécables (milliers) sont remplacés par des espaces dans les tests.
1 po = 25.4 mm ; 1 pi = 304.8 mm ; 1 lb = 4.4482216 N (moteur/commun/unites.py).
2x6 S-P-F n° 1/n° 2 : f_cp = 5.3 MPa, K_D = K_Scp = K_T = K_B = K_Zcp = 1.00 (voir test_page_k_d.py).
"""

from tests.test_acces import _connecte

DIMENSIONS, CHARGES = "unites_dimensions", "unites_charges"


def _basculer(at, cle, systeme):
    [b for b in at.sidebar.get("button_group") if b.key == cle][0].set_value(systeme).run()
    assert not at.exception
    return at


def _champ(at, debut):
    return [t for t in at.text_input if t.label.startswith(debut)][0]


def _entrer(at, debut, texte):
    _champ(at, debut).set_value(texte).run()
    assert not at.exception
    return at


def _qr(at):
    return [m.value.replace("\u00a0", " ") for m in at.markdown if m.value.startswith("$Q_r")]


def _conversions(at):
    return [c.value.replace("\u00a0", " ") for c in at.caption if c.value.startswith("= ")]


def test_par_defaut():
    """Au départ : dimensions en impérial, charges en métrique (décision de l'utilisateur)."""
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    bascule = {b.key: b.value for b in at.sidebar.get("button_group")}
    assert bascule[DIMENSIONS] == "Impérial" and bascule[CHARGES] == "Métrique"
    libelles = [t.label for t in at.text_input]
    # Unité par défaut entre parenthèses
    assert "Longueur d'appui, $L_b$ (po)" in libelles
    assert "Longueur de l'élément, $L$ (pi)" in libelles
    assert "$R_f: (kN)$" in libelles
    assert "$M_f: (kN \\cdot m)$" in libelles
    # Dimensions nettes dans les deux unités : 38 mm / 25.4 mm/po = 1.496 po -> 1 1/2 po ;
    # 140 mm / 25.4 mm/po = 5.512 po -> 5 1/2 po (au 1/16 po près)
    assert [m.value for m in at.metric] == ["38 mm (1 1/2 po)", "140 mm (5 1/2 po)"]
    # Les dimensions nominales restent en po (« 2x6 »), même si les dimensions par défaut sont en mm :
    # la boîte « Pièce » (datum-retours #20) lit les nombres sans unité en po
    assert [t for t in at.text_input if t.key == "piece"][0].value == "2x6"


def test_element_compose():
    at = _connecte("admin", "mot-admin")
    [t for t in at.text_input if t.key == "piece"][0].set_value("2 2x6").run()  # 2 plis de 2x6 (datum-retours #20)
    # 2 x 38 mm = 76 mm ; 76 mm / 25.4 mm/po = 2.992 po -> 3 po (au 1/16 po près)
    assert at.metric[0].value == "2*38 = 76 mm (3 po)"


def test_unites_melangees():
    """Exemple de l'utilisateur : 8 pi 38 mm = 8 x 304.8 mm + 38 mm = 2476.4 mm (97.5 po = 8 pi 1 1/2 po)."""
    at = _entrer(_connecte("admin", "mot-admin"), "Longueur de l'élément", "8 pi 38 mm")
    assert "= 2 476.4 mm (8 pi 1 1/2 po)" in _conversions(at)


def test_toute_unite_dans_tout_champ():
    """
    L_b = 3 1/2 po = 88.9 mm ; R_f = 1124 lb = 1124 x 4.4482 N = 5000 N = 5.00 kN.
    Q_r = 0.8 x 5.3 MPa x (38 mm x 88.9 mm) = 0.8 x 5.3 MPa x 3378.2 mm² = 14 323.6 N -> 14.3 kN ;
    14 323.6 N / 4.4482 N/lb = 3220 lb (3 chiffres significatifs, comme le Résumé et la note PDF : issue #98).
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "3 1/2 po")
    _entrer(at, "$R_f", "1124 lb")
    assert "= 88.9 mm (3 1/2 po)" in _conversions(at)
    assert "= 5.00 kN (1 124 lb)" in _conversions(at)
    assert _qr(at) == ["$Q_r = \\text{14.3 kN (3 220 lb)}$"]
    # Ratio : 5.00 kN / 14.32 kN = 34.91 %
    assert any("34.91%" in s.value for s in at.success)


def test_nombre_sans_unite_dans_l_unite_par_defaut():
    """Dimensions en impérial au départ : « 3 1/2 » = 3.5 po = 88.9 mm ; charges en kN : « 5 » = 5 kN."""
    at = _connecte("admin", "mot-admin")
    assert _champ(at, "Longueur d'appui").label == "Longueur d'appui, $L_b$ (po)"
    assert _champ(at, "Longueur de l'élément").label == "Longueur de l'élément, $L$ (pi)"
    assert _champ(at, "$R_f").label == "$R_f: (kN)$"  # bascules indépendantes
    _entrer(at, "Longueur d'appui", "3 1/2")
    _entrer(at, "$R_f", "5")
    assert _qr(at) == ["$Q_r = \\text{14.3 kN (3 220 lb)}$"]
    # Charges en impérial par défaut : « 1124 » = 1124 lb = 5.00 kN
    _basculer(at, CHARGES, "Impérial")
    assert _champ(at, "$R_f").label == "$R_f: (lb)$"
    assert _champ(at, "$M_f").label == "$M_f: (lb \\cdot po)$"
    _entrer(at, "$R_f", "1124")
    assert "= 5.00 kN (1 124 lb)" in _conversions(at)


def test_valeur_entree_garde_son_sens():
    """
    « 89 » entré en mm (unité par défaut choisie) reste 89 mm quand l'unité par défaut passe à l'impérial.
    Q_r = 0.8 x 5.3 MPa x (38 mm x 89 mm) = 14 340 N -> 14.3 kN (3 220 lb) ; 5 kN / 14.340 kN = 34.87 %.
    Avec 88.9 mm : Q_r = 14 323.6 N -> 14.3 kN aussi ; 5 kN / 14.3236 kN = 34.91 % (le ratio les distingue).
    """
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Métrique")
    _entrer(at, "Longueur d'appui", "89")
    _entrer(at, "$R_f", "5")
    assert _qr(at) == ["$Q_r = \\text{14.3 kN (3 220 lb)}$"]
    _basculer(at, DIMENSIONS, "Impérial")
    _basculer(at, CHARGES, "Impérial")
    assert _champ(at, "Longueur d'appui").value == "89"
    assert _qr(at) == ["$Q_r = \\text{14.3 kN (3 220 lb)}$"]
    assert any("34.87%" in s.value for s in at.success)
    assert "= 89 mm (3 1/2 po)" in _conversions(at)
    # Le texte modifié est relu avec la nouvelle unité par défaut : « 3 1/2 » = 88.9 mm
    _entrer(at, "Longueur d'appui", "3 1/2")
    assert _qr(at) == ["$Q_r = \\text{14.3 kN (3 220 lb)}$"]
    assert any("34.91%" in s.value for s in at.success)


def test_methode_de_travail():
    """
    Exemple de l'utilisateur : longueur d'appui en po, entaille en mm, largeur d'appui en po.
    L_b = 3 1/2 po = 88.9 mm ; d_n = 20 mm ; b = 1 1/4 po = 31.75 mm.
    Q_r = 0.8 x 5.3 MPa x (31.75 mm x 88.9 mm) = 0.8 x 5.3 MPa x 2822.6 mm² = 11 967.7 N -> 12.0 kN ;
    5 kN / 11.9677 kN = 41.78 %
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "$R_f", "5 kN")
    _entrer(at, "Longueur d'appui", "3 1/2 po")
    _entrer(at, "Profondeur de l'entaille", "20 mm")
    _entrer(at, "Largeur d'appui", "1 1/4\"")
    assert _qr(at)[0].startswith("$Q_r = \\text{12.0 kN")
    assert any("41.78%" in s.value for s in at.success)
    assert "= 31.8 mm (1 1/4 po)" in _conversions(at)  # 31.75 mm, au dixième de mm
    assert "= 20 mm (13/16 po)" in _conversions(at)  # 20 mm / 25.4 = 0.787 po -> 13/16 po


def test_longueur_en_pieds_et_pouces():
    """L = 8' 6" = 8 pi 6 po = 102 po x 25.4 mm/po = 2590.8 mm ; 3 pi 2 1/4 po = 38.25 po = 971.55 mm."""
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur de l'élément", "8' 6\"")
    assert "= 2 590.8 mm (8 pi 6 po)" in _conversions(at)
    _entrer(at, "Longueur de l'élément", "3 pi 2 1/4 po")
    # 971.55 mm, au dixième de mm (arrondi binaire de 971.55 : 971.5 ou 971.6)
    assert any(c.endswith("mm (3 pi 2 1/4 po)") and c.startswith("= 971.") for c in _conversions(at))


def test_moments_en_toutes_unites():
    """M_f = 40 000 lb·po = 40 000 x 4.4482 N x 25.4 mm = 4 519 393 N·mm = 4.52 kN·m."""
    at = _entrer(_connecte("admin", "mot-admin"), "$M_f", "40 000 lb·po")
    assert "= 4.52 kN·m (40 000 lb·po)" in _conversions(at)


def test_valeur_illisible():
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "trois")
    assert any("« trois » : texte illisible" in e.value for e in at.error)
    _entrer(at, "$R_f", "5 mm")  # unité d'une autre grandeur
    assert any("« 5 mm » : texte illisible, ou unité qui ne convient pas à une force" in e.value
               for e in at.error)


def test_entaille_a_la_limite():
    """
    d_n <= 0.25 d = 0.25 x 140 mm = 35 mm (6.5.4.4.2). 35 mm est accepté ; 1.38 po = 35.05 mm est refusé ;
    1 3/8 po = 34.925 mm est accepté.
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur de l'entaille", "100 mm")
    _entrer(at, "$V_f", "1")
    _entrer(at, "Profondeur de l'entaille", "35 mm")
    assert [m.value for m in at.markdown if m.value.startswith("$F_r")]
    _entrer(at, "Profondeur de l'entaille", "1.38 po")
    assert any("ne doit pas dépasser 35 mm (1.378 po)" in e.value for e in at.error)
    assert not [m.value for m in at.markdown if m.value.startswith("$F_r")]
    _entrer(at, "Profondeur de l'entaille", "1 3/8 po")
    assert not at.error
    assert [m.value for m in at.markdown if m.value.startswith("$F_r")]


def test_longueur_d_appui_au_moins_1_mm():
    at = _entrer(_connecte("admin", "mot-admin"), "Longueur d'appui", "0.5 mm")
    assert any("au moins 1 mm" in e.value for e in at.error)


def test_resume_en_metrique_seulement():
    """
    datum-retours #22 : le résumé est en métrique seulement (l'onglet garde les deux unités, PR #99).
    V_f = 1 kN -> « 1.00 kN » (3 chiffres significatifs), sans « (225 lb) ».
    """
    at = _entrer(_connecte("admin", "mot-admin"), "$V_f", "1 kN")
    (tableau,) = [m.value for m in at.markdown if m.value.startswith("| Article")]
    ligne = next(l for l in tableau.splitlines() if "6.5.4.3" in l)
    assert "$V_f$ = 1.00 kN**" in ligne and "lb" not in ligne  # seule vérification faite : en gras


def test_k_d_unite_de_pression():
    """K_D (5.3.2.2) : seul le rapport P_L / P_s compte ; l'unité affichée suit la bascule des charges."""
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Durée")][0].set_value("Continue (permanente)").run()
    [c for c in at.checkbox if c.key == "kd_charges"][0].check().run()
    assert any(n.label == "$P_L$ (kPa)" for n in at.number_input)
    _basculer(at, CHARGES, "Impérial")
    assert any(n.label == "$P_L$ (lb/pi²)" for n in at.number_input)


def test_somme_avec_plus():
    """
    « 2 + 3 po » = 5 po x 25.4 mm/po = 127 mm (un nombre sans unité prend l'unité du terme suivant) ;
    « 1500 lb + 2 kN » = 1500 x 4.4482 N + 2000 N = 8672.3 N = 8.67 kN.
    """
    at = _basculer(_connecte("admin", "mot-admin"), DIMENSIONS, "Métrique")  # même en mm par défaut
    _entrer(at, "Longueur d'appui", "2 + 3 po")
    assert "= 127 mm (5 po)" in _conversions(at)
    _entrer(at, "$R_f", "1500 lb + 2 kN")
    assert "= 8.67 kN (1 950 lb)" in _conversions(at)


def test_resultats_lisibles():
    """Résultats dans \\text{} (espaces et unités droites) et milliers séparés (« 5 060 lb »)."""
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "3 1/2")
    _entrer(at, "$R_f", "5")
    (qr,) = [m.value for m in at.markdown if m.value.startswith("$Q_r")]
    # Espace insécable entre les milliers : 14 323.6 N / 4.4482 N/lb = 3220 lb -> « 3 220 lb »
    assert qr == "$Q_r = \\text{14.3 kN (3\u00a0220 lb)}$"


def test_calculatrice():
    """
    Les champs calculent (décisions de l'utilisateur) :
    « (2+3)/2 » = 2.5 po (dimensions en impérial au départ) = 63.5 mm ;
    « 8 pieds + 36 po - 50 mm » = 2438.4 mm + 914.4 mm - 50 mm = 3302.8 mm ;
    « 8-6 » = 8 - 6 = 2 pi (« - » est toujours une soustraction) = 609.6 mm ;
    « 3*4 kN » = 12 kN.
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "(2+3)/2")
    assert "= 63.5 mm (2 1/2 po)" in _conversions(at)
    _entrer(at, "Longueur de l'élément", "8 pieds + 36 po - 50 mm")
    # 3302.8 mm / 25.4 mm/po = 130.0315 po x 16 = 2080.504 -> 2081/16 po = 130 1/16 po = 10 pi 10 1/16 po
    assert "= 3 302.8 mm (10 pi 10 1/16 po)" in _conversions(at)
    _entrer(at, "Longueur de l'élément", "8-6")
    assert "= 609.6 mm (2 pi 0 po)" in _conversions(at)
    _entrer(at, "$R_f", "3*4 kN")
    assert "= 12.00 kN (2 698 lb)" in _conversions(at)  # 12 000 N / 4.4482 N/lb = 2697.7 lb


def test_virgule_decimale():
    """« 3,5 po » = « 3.5 po » = 88.9 mm ; « 4,5 kN » = 4.50 kN (1 012 lb : 4500 N / 4.4482 N/lb)."""
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "3,5 po")
    assert "= 88.9 mm (3 1/2 po)" in _conversions(at)
    _entrer(at, "$R_f", "4,5 kN")
    assert "= 4.50 kN (1 012 lb)" in _conversions(at)


def test_message_court_et_multiplication():
    """
    « 2 po * 3 po » = 6 po = 152.4 mm (même unité comptée une fois) ; « 2 po * 3 mm » est refusé avec la
    raison, en un message court (les exemples restent dans l'aide).
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "Longueur d'appui", "2 po * 3 po")
    assert "= 152.4 mm (6 po)" in _conversions(at)
    _entrer(at, "Longueur d'appui", "2 po * 3 mm")
    (erreur,) = [e.value for e in at.error]
    assert erreur.startswith("« 2 po * 3 mm » : multiplication de deux unités différentes")
    assert len(erreur) < 150 and "Calculs permis" not in erreur


def test_negatifs_et_zero_dans_la_page():
    """
    Calculs de base : valeurs positives seulement (CLAUDE.md). Une charge négative est refusée ; une
    dimension doit être d'au moins 1 mm ; une charge nulle est permise ; aucune exception.
    """
    cas = [
        ("$R_f", "-5", "La valeur ne peut pas être négative."),
        ("$M_f", "-2 kN·m", "La valeur ne peut pas être négative."),
        ("Profondeur de l'entaille", "-1 po", "La valeur ne peut pas être négative."),
        ("Longueur d'appui", "5 - 10 po", "La valeur doit être d'au moins 1 mm (1/16 po)."),
        ("Longueur d'appui", "0", "La valeur doit être d'au moins 1 mm (1/16 po)."),
        ("Longueur de l'élément", "-8 pi", "La valeur doit être d'au moins 1 mm (0 pi 1/16 po)."),
        ("$V_f", "5 kN / 0", "« 5 kN / 0 » : division par zéro. Exemples dans l'aide (?)."),
        ("Longueur de l'élément", "10^400", "« 10^400 » : nombre trop grand. Exemples dans l'aide (?)."),
    ]
    for debut, texte, message in cas:
        at = _entrer(_connecte("admin", "mot-admin"), debut, texte)
        assert [e.value for e in at.error] == [message], (debut, texte)
    # Charge nulle : permise, sans « -0 »
    at = _entrer(_connecte("admin", "mot-admin"), "$R_f", "-0")
    assert not at.error and "= 0.00 kN (0 lb)" in _conversions(at)
