"""Page Bois de sciage : K_D calculé à partir des charges (5.3.2.2, issue #58)."""

from tests.test_acces import _connecte


def _qr(at):
    return [m.value for m in at.markdown if m.value.startswith("$Qr")]


def _preparer(p_l, neige, surcharge):
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Durée")][0].set_value("Continue (permanente)").run()
    [c for c in at.checkbox if c.key == "kd_charges"][0].check().run()
    for cle, valeur in (("kd_p_l", p_l), ("kd_s", neige), ("kd_l", surcharge)):
        [n for n in at.number_input if n.key == cle][0].set_value(valeur)
    at.run()
    for cle, valeur in (("cp_support_length", 89.0), ("cp_rf", 5.0)):  # mm ; kN
        [n for n in at.number_input if n.key == cle][0].set_value(valeur)
    return at.run()


def test_k_d_par_les_charges():
    # P_L = 3 kPa, S = 2 kPa, L = 1 kPa : P_s = max(2, 1, 2 + 0.5, 1 + 1) = 2.5 kPa
    # K_D = 1 - 0.5 log(3 / 2.5) = 1 - 0.5 x 0.07918 = 0.96041
    at = _preparer(3.0, 2.0, 1.0)
    assert not at.exception
    assert any("P_s = 2.50" in m.value and "K_D = 0.960" in m.value for m in at.markdown)
    # 2x6 S-P-F n° 1/n° 2 (f_cp = 5.3 MPa), appui 38 mm x 89 mm, K_B = K_Zcp = 1.00 :
    # Q_r = 0.8 x 5.3 MPa x 0.96041 x 3382 mm² = 13 772 N = 13.77 kN
    assert _qr(at) == ["$Qr = 13.77 kN$"]


def test_charge_continue_qui_ne_domine_pas():
    # P_L = 2 kPa <= P_s = 2.5 kPa : K_D = 1.00 (5.3.2.2 ne s'applique pas), avec un avertissement
    at = _preparer(2.0, 2.0, 1.0)
    assert not at.exception
    assert any("K_D = 1.000" in m.value for m in at.markdown)
    assert any("ne domine pas" in w.value for w in at.warning)
    # Q_r = 0.8 x 5.3 MPa x 1.00 x 3382 mm² = 14 340 N = 14.34 kN
    assert _qr(at) == ["$Qr = 14.34 kN$"]


def test_sans_charges_tableau_5_1():
    # Durée continue sans charges : K_D = 0.65 (tableau 5.1)
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Durée")][0].set_value("Continue (permanente)").run()
    [c for c in at.checkbox if c.key == "kd_charges"][0].check().run()
    for cle, valeur in (("cp_support_length", 89.0), ("cp_rf", 5.0)):
        [n for n in at.number_input if n.key == cle][0].set_value(valeur)
    at.run()
    assert not at.exception
    assert any("tableau 5.1" in i.value for i in at.info)
    # Q_r = 0.8 x 5.3 MPa x 0.65 x 3382 mm² = 9 321 N = 9.32 kN
    assert _qr(at) == ["$Qr = 9.32 kN$"]



def _images(noeud) -> int:
    """Nombre d'images (st.image) dans la page."""
    enfants = getattr(noeud, "children", {}).values()
    return sum((getattr(e, "type", None) == "image") + _images(e) for e in enfants)


def test_figure_de_la_compression_perpendiculaire():
    """
    Issue #62 et retour #14 : la figure de 6.5.6.2 s'affiche dès l'ouverture de l'onglet, avant
    d'entrer L_b, puis reste affichée (la même figure, tirée du calcul).
    """
    at = _connecte("admin", "mot-admin")
    assert any("Lb" in t and "Rf" in t for t in _figures_svg(at._tree))
    avant = _images(at._tree)
    [n for n in at.number_input if n.key == "cp_support_length"][0].set_value(89.0).run()  # mm
    assert not at.exception
    assert _images(at._tree) == avant


def test_figure_d_un_element_compose():
    """Issue #62 : avec 3 plis, la page passe le nombre de plis à la trace (figure)."""
    at = _connecte("admin", "mot-admin")
    [r for r in at.radio if r.label.startswith("Élément composé")][0].set_value(3).run()
    [n for n in at.number_input if n.key == "cp_support_length"][0].set_value(89.0).run()  # mm
    assert not at.exception
    assert _images(at._tree) >= 1


def test_figure_de_la_compression_pres_d_un_appui():
    """
    Issue #62 et retour #14 : la figure de 6.5.6.3 s'affiche avant d'entrer les longueurs d'appui,
    puis reste affichée une fois les deux longueurs entrées.
    """
    at = _connecte("admin", "mot-admin")
    assert any("Lb1" in t and "Lb2" in t for t in _figures_svg(at._tree))
    [n for n in at.number_input if n.key == "cp_support_length"][0].set_value(89.0).run()  # mm
    avant = _images(at._tree)
    [c for c in at.checkbox if c.key == "cp_near_load"][0].check().run()
    [n for n in at.number_input if n.key == "cp_load_length"][0].set_value(38.0).run()  # mm
    assert not at.exception
    assert _images(at._tree) == avant


def _figures_svg(noeud) -> list[str]:
    """Figures schématiques (SVG) affichées dans la page, décodées."""
    import base64
    import re

    figures = []
    for e in getattr(noeud, "children", {}).values():
        if getattr(e, "type", None) == "image":
            for image in e.proto.imgs:
                if image.url.startswith("data:image/svg+xml;base64,"):
                    svg = base64.b64decode(image.url.split(",", 1)[1]).decode()
                    figures.append(re.sub(r"<[^>]+>", "", svg).replace("​", ""))
        figures += _figures_svg(e)
    return figures


def test_figures_de_la_flexion_et_du_cisaillement():
    """Issue #62 : les onglets Flexion et Cisaillement affichent leur figure (symboles seulement)."""
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    textes = _figures_svg(at._tree)
    assert any("Mf" in t for t in textes)  # 6.5.3
    assert any("Vf" in t and "dn" not in t for t in textes)  # 6.5.4.3


def test_figures_avant_les_valeurs():
    """
    Retours #9, #11 et #13 : à l'ouverture, sans valeurs entrées, chaque onglet affiche sa figure :
    flexion, cisaillement, entaille (d_n, e), compression parallèle, compression perpendiculaire et
    compression près d'un appui. L'ancienne image de l'entaille (PNG) n'est plus affichée.
    """
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    textes = _figures_svg(at._tree)
    assert any("Mf" in t for t in textes)  # 6.5.3
    assert any("Vf" in t and "dn" not in t for t in textes)  # 6.5.4.3
    assert any("dn" in t and "e" in t for t in textes)  # 6.5.4.4, figure 6.1
    assert any("Pf" in t and "Ke(b)" in t and "L(d)" in t for t in textes)  # 6.5.5 (6.5.5.1)
    assert any("Lb" in t and "Rf" in t for t in textes)  # 6.5.6.2
    assert any("Lb1" in t and "Lb2" in t for t in textes)  # 6.5.6.3
    assert len(textes) == _images(at._tree)  # seulement des figures SVG, plus d'image PNG


def test_aide_de_la_profondeur_de_l_entaille():
    """Retour #18 : l'aide de d_n est en LaTeX valide (pas d'espace après « $ »), avec un point."""
    at = _connecte("admin", "mot-admin")
    aide = [n for n in at.number_input if n.label.startswith("Profondeur de l'entaille")][0].help
    # 2x6 : d = 140 mm ; 0.25 x 140 mm = 35.0 mm (1.38 po)
    assert aide == "Ne doit pas dépasser $0.25 \\cdot d = 35.0$ mm (6.5.4.4.2)"


def test_largeur_d_appui_preremplie():
    """
    Retour #15 : la largeur d'appui b est préremplie avec la largeur de l'élément, et suit un
    changement du nombre de plis.
    """
    at = _connecte("admin", "mot-admin")
    champ = lambda: [n for n in at.number_input if n.key == "cp_bearing_width"][0]  # noqa: E731
    assert champ().value == 38.0  # 2x6 : b = 38 mm (1.50 po)
    [r for r in at.radio if r.label.startswith("Élément composé")][0].set_value(2).run()
    assert not at.exception
    assert champ().value == 76.0  # 2 plis x 38 mm = 76 mm (2.99 po)
    # Une valeur entrée par l'utilisateur est gardée tant que l'élément ne change pas
    champ().set_value(50.0).run()  # mm
    [n for n in at.number_input if n.key == "cp_support_length"][0].set_value(89.0).run()  # mm
    assert champ().value == 50.0


def _compression_parallele(at):
    """2x6 (38 x 140 mm), L = 3000 mm, L_(b) = 1500 mm, L_(d) = 3000 mm."""
    [n for n in at.number_input if n.label.startswith("Longueur de l'élément")][0].set_value(3000)  # mm
    [n for n in at.number_input if n.key == "cpa_L_selon_b"][0].set_value(1500)  # mm
    [n for n in at.number_input if n.key == "cpa_L_selon_d"][0].set_value(3000)  # mm
    at.run()
    [n for n in at.number_input if n.label.startswith("$Pf")][0].set_value(5.0)  # kN
    return at.run()


def _c_c(at) -> list[str]:
    return [m.value.split("$C_c = ")[1].split("$")[0] for m in at.markdown if "$C_c = " in m.value]


def _bouton(at, cle):
    return [b for b in at.button if b.key == cle][0]


def test_compression_parallele_entraxes_et_k_e():
    """
    La page demande L pour chaque axe (6.5.5.1) ; la figure de 6.5.5 s'affiche. Par défaut, K_e = 1.00
    (tableau A.4 : translation fixe et rotation libre aux deux extrémités ; issue #90).
    """
    at = _compression_parallele(_connecte("admin", "mot-admin"))
    assert not at.exception
    assert any("Ke(b)" in t and "L(d)" in t for t in _figures_svg(at._tree))
    # C_c(b) = 1.00 x 1500 mm / 38 mm = 39.47 ; C_c(d) = 1.00 x 3000 mm / 140 mm = 21.43
    assert _c_c(at) == ["39.47", "21.43"]
    assert _bouton(at, "cpa_degre_selon_b_2").proto.type == "primary"  # 3e ligne : 1.00
    assert _bouton(at, "cpa_degre_selon_d_2").proto.type == "primary"
    assert not [n for n in at.number_input if n.key == "cpa_K_e_selon_b"]  # pas de K_e à entrer


def test_k_e_choisi_avec_les_icones_du_tableau_a_4():
    """
    Issue #90 : un bouton sous chaque icône du tableau A.4 choisit K_e, pour chaque axe séparément.
    Selon b : 2e ligne (translation fixe aux deux extrémités et rotation fixe à une extrémité, 0.80) ;
    selon d : 7e ligne (translation et rotation libres à l'autre extrémité, 2.00).
    """
    at = _compression_parallele(_connecte("admin", "mot-admin"))
    _bouton(at, "cpa_degre_selon_b_1").click().run()
    _bouton(at, "cpa_degre_selon_d_6").click().run()
    assert not at.exception
    # C_c(b) = 0.80 x 1500 mm / 38 mm = 1200 mm / 38 mm = 31.58
    # C_c(d) = 2.00 x 3000 mm / 140 mm = 6000 mm / 140 mm = 42.86
    assert _c_c(at) == ["31.58", "42.86"]
    assert _bouton(at, "cpa_degre_selon_b_1").proto.type == "primary"
    assert _bouton(at, "cpa_degre_selon_b_2").proto.type == "secondary"
    # K_e affiché (non modifiable) dans le champ de chaque axe
    affiches = {n.label: n.value for n in at.number_input if n.label.startswith("$K_{e(")}
    assert affiches == {"$K_{e(b)}$": 0.80, "$K_{e(d)}$": 2.00}


def test_k_e_autre_entre_par_l_utilisateur():
    """Issue #90 : « Autre » permet d'entrer K_e, sans avertissement (choix de l'ingénieur)."""
    at = _compression_parallele(_connecte("admin", "mot-admin"))
    _bouton(at, "cpa_degre_selon_b_autre").click().run()
    champ = [n for n in at.number_input if n.key == "cpa_K_e_selon_b"][0]
    assert champ.value == 1.00
    champ.set_value(0.60).run()  # plus petit que toutes les valeurs du tableau A.4 : permis
    assert not at.exception
    assert not [w for w in at.warning if "K_e" in w.value or "A.4" in w.value]
    # C_c(b) = 0.60 x 1500 mm / 38 mm = 900 mm / 38 mm = 23.68 ; C_c(d) inchangé : 21.43
    assert _c_c(at) == ["23.68", "21.43"]
    assert _bouton(at, "cpa_degre_selon_b_autre").proto.type == "primary"


def test_icones_du_tableau_a_4_dans_l_onglet():
    """Issue #90 : 7 icônes du tableau A.4 par axe (b et d), aux couleurs du compte."""
    import config
    from moteur.commun.figures import icones_des_degres_de_retenue

    at = _connecte("admin", "mot-admin")
    apparence = config.apparence_du_compte("admin")
    attendues = icones_des_degres_de_retenue(apparence.principale, apparence.accent)
    icones = _icones_svg(at._tree)
    assert sum(i in attendues for i in icones) == 14
    for i in range(7):
        assert [b.label for b in at.button if b.key == f"cpa_degre_selon_b_{i}"] == [
            ["0.65", "0.80", "1.00", "1.20", "1.50", "2.00", "2.00"][i]
        ]


def _icones_svg(noeud) -> list[str]:
    """Petites icônes (SVG 64 x 64 de marque/icones/) affichées dans la page, décodées."""
    import base64

    icones = []
    for e in getattr(noeud, "children", {}).values():
        if getattr(e, "type", None) == "image":
            for image in e.proto.imgs:
                if image.url.startswith("data:image/svg+xml;base64,"):
                    svg = base64.b64decode(image.url.split(",", 1)[1]).decode()
                    if 'viewBox="0 0 64 64"' in svg:
                        icones.append(svg)
        icones += _icones_svg(e)
    return icones


def test_icones_en_haut_des_onglets():
    """
    Issue #89 : chaque onglet commence par son titre et les icônes de ses vérifications, aux couleurs
    du compte : flexion (1), cisaillement et entaille (2), compression parallèle (1), compression
    perpendiculaire et près d'un appui (2), traction (1), flexion et charge axiale (1). La compression
    oblique n'a pas d'icône : 8 icônes en tout.
    """
    import config
    from moteur.commun.figures import icone, icones_des_degres_de_retenue

    at = _connecte("admin", "mot-admin")
    assert not at.exception
    apparence = config.apparence_du_compte("admin")
    a_4 = icones_des_degres_de_retenue(apparence.principale, apparence.accent)
    icones = [i for i in _icones_svg(at._tree) if i not in a_4]  # sans celles du tableau A.4 (#90)
    noms = [
        "flexion", "cisaillement", "cisaillement_entaille", "compression_parallele",
        "compression_perpendiculaire", "compression_pres_appui", "traction", "flexion_et_charge_axiale",
    ]
    assert icones == [icone(n, apparence.principale, apparence.accent) for n in noms]
    titres = [m.value for m in at.markdown if m.value.startswith("**") and "(6.5." in m.value]
    assert titres == [
        "**Moment de flexion (6.5.3)**",
        "**Cisaillement (6.5.4)**",
        "**Compression parallèle au fil (6.5.5)**",
        "**Compression perpendiculaire au fil (6.5.6)**",
        "**Compression oblique par rapport au fil (6.5.7)**",
        "**Traction parallèle au fil (6.5.8)**",
        "**Flexion et charge axiale combinées (6.5.9)**",
    ]
