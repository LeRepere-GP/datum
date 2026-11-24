"""Figures schématiques des vérifications (moteur/commun/figures.py, issue #62)."""

import re

import pytest

from moteur.commun.figures import figure, figure_avant_le_calcul
from moteur.commun.resultat import Resultat
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_6_resistance_a_la_compression_perpendiculaire_au_fil as art_6_5_6,
)


def _texte(svg: str) -> str:
    """Texte visible du SVG, sans balises ni espace sans chasse."""
    return re.sub(r"<[^>]+>", "", svg).replace("​", "")


def _appui(**kwargs) -> Resultat:
    donnees = dict(b=38, d=184, L_b=89, f_cp=5.3, largeur_element=38)  # mm ; MPa
    donnees.update(kwargs)
    return art_6_5_6.verifier_compression_perpendiculaire_au_fil(**donnees)


def test_compression_perpendiculaire_symboles_sans_valeurs():
    """Symboles seulement : les valeurs sont dans le tableau des données (demande de l'utilisateur)."""
    svg = figure(_appui(R_f=12))  # kN
    assert svg.startswith("<svg")
    texte = _texte(svg)
    for symbole in ("Lb", "Rf", "b", "d"):
        assert symbole in texte
    assert not any(c.isdigit() for c in texte)  # aucun chiffre dans l'image
    assert "mm" not in texte and "kN" not in texte


def test_appui_plus_etroit_que_l_element():
    # b = 30 mm < b_élément = 89 mm : l'appui est dessiné plus étroit que la section (28 contre 40)
    assert "width='28'" in figure(_appui(b=30, largeur_element=89))
    assert "width='28'" not in figure(_appui())


def test_couleurs_du_compte():
    svg = figure(_appui(R_f=12), principale="#112233", accent="#AA5500")
    assert "#112233" in svg and "#AA5500" in svg
    assert "#233614" not in svg and "#9E5A00" not in svg


def test_verification_sans_figure():
    assert figure(Resultat("CSA O86:19", "6.5.8", "Traction")) is None  # pas encore de figure


def test_bois_de_bout_avec_un_x():
    """Convention de dessin : l'élément vu en bout porte un X (figure 6.1) ; les appuis sont hachurés."""
    svg = figure(_appui(R_f=12))
    # X sur l'élément en section (x 196 à 236 ; y 20 à 66) seulement
    assert "M196 20 L236 66 M236 20 L196 66" in svg
    assert "M14 66 L60 90" not in svg  # l'appui en élévation n'a pas de X


def test_element_compose_chaque_pli_avec_son_x():
    """Poutre composée : chaque pli est dessiné vu en bout, avec son X (demande de l'utilisateur)."""
    # 3-2x10 : 3 plis de 38 mm = 114 mm ; largeur d'un pli dans la figure = 76 / 3
    r = _appui(b=114, d=235, largeur_element=114, plis=3)
    svg = figure(r)
    assert svg.count("stroke-width='2.5'/><path") == 3  # 3 rectangles vus en bout, chacun avec un X
    assert any(d.symbole == "" and d.description == "Nombre de plis" and d.valeur == 3 for d in r.donnees)


def test_un_seul_pli_sans_donnee_de_plis():
    r = _appui()
    assert figure(r).count("stroke-width='2.5'/><path") == 1
    assert all(d.description != "Nombre de plis" for d in r.donnees)  # pas de ligne inutile dans la note


def _pres_d_un_appui(**kwargs) -> Resultat:
    donnees = dict(b=38, d=184, L_b_appui=89, L_b_charge=38, f_cp=5.3, largeur_element=38)  # mm ; MPa
    donnees.update(kwargs)
    return art_6_5_6.verifier_compression_perpendiculaire_pres_d_un_appui(**donnees)


def test_compression_pres_d_un_appui_symboles_sans_valeurs():
    texte = _texte(figure(_pres_d_un_appui(P_f=5)))  # kN
    for symbole in ("Pf", "≤ d", "b"):
        assert symbole in texte
    # Aucun chiffre dans l'image, sauf les indices de L_b1 et L_b2 (symboles de 6.5.6.3.2)
    assert not any(c.isdigit() for c in texte.replace("Lb1", "").replace("Lb2", ""))


def test_l_b1_est_la_plus_petite_longueur_d_appui():
    """6.5.6.3.2 (p. 72) : L_b1 = longueur d'appui la plus petite, L_b2 = la plus grande."""
    # Charge 38 mm < appui 89 mm : L_b1 sur le dessus (charge), L_b2 à l'appui
    r = _pres_d_un_appui(L_b_appui=89, L_b_charge=38)  # mm
    donnees = {d.symbole: (d.valeur, d.description) for d in r.donnees}
    assert donnees["L_{b1}"] == (38, "Longueur d'appui la plus petite (charge)")
    assert donnees["L_{b2}"] == (89, "Longueur d'appui la plus grande (appui)")
    svg = figure(r)
    assert svg.index(">L<tspan dy='4' font-size='75%'>b1<") < svg.index(">L<tspan dy='4' font-size='75%'>b2<")
    # Appui 38 mm < charge 89 mm : les symboles s'inversent
    r = _pres_d_un_appui(L_b_appui=38, L_b_charge=89)  # mm
    donnees = {d.symbole: (d.valeur, d.description) for d in r.donnees}
    assert donnees["L_{b1}"] == (38, "Longueur d'appui la plus petite (appui)")
    assert donnees["L_{b2}"] == (89, "Longueur d'appui la plus grande (charge)")
    svg = figure(r)
    assert svg.index(">L<tspan dy='4' font-size='75%'>b2<") < svg.index(">L<tspan dy='4' font-size='75%'>b1<")
    # Longueurs égales : L_b1 est celle de la charge, comme à la figure 6.2 (p. 71)
    r = _pres_d_un_appui(L_b_appui=89, L_b_charge=89)  # mm
    assert dict((d.symbole, d.description) for d in r.donnees)["L_{b1}"].endswith("(charge)")
    # A'_b inchangé : 38 mm x (38 mm + 89 mm) / 2 = 2413 mm² <= 1.5 x 38 mm x 38 mm = 2166 mm²
    # -> A'_b = 2166 mm² dans les deux cas
    for appui, charge in ((89, 38), (38, 89)):
        r = _pres_d_un_appui(L_b_appui=appui, L_b_charge=charge)
        assert r.etape("A'_b").valeur == 2166


def test_compression_pres_d_un_appui_plis():
    r = _pres_d_un_appui(b=114, d=235, largeur_element=114, plis=3)
    svg = figure(r)
    assert svg.count("stroke-width='2.5'/><path") == 3  # 3 plis vus en bout, chacun avec un X
    assert any(d.symbole == "" and d.description == "Nombre de plis" and d.valeur == 3 for d in r.donnees)



# --- Flexion, cisaillement, entaille et compression parallèle (issue #62) ---

from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (  # noqa: E402
    art_6_5_3_resistance_au_moment_de_flexion as art_6_5_3,
    art_6_5_4_resistance_au_cisaillement as art_6_5_4,
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art_6_5_5,
)


def _sans_chiffres(texte: str, *symboles_avec_chiffres: str) -> bool:
    for s in symboles_avec_chiffres:
        texte = texte.replace(s, "")
    return not any(c.isdigit() for c in texte)


def test_flexion():
    # 3-2x10 : 3 plis de 38 mm x 235 mm, plis fixés à au plus 4 d (6.5.3.2.4)
    r = art_6_5_3.verifier_flexion(
        b=38, d=235, f_b=11.8, plis=3, M_f=5,  # mm ; MPa ; kN·m
        support_lateral_aux_appuis=True, rive_comprimee_maintenue=True,
        plis_fixes_a_au_plus_4d=True,
    )
    svg = figure(r)
    texte = _texte(svg)
    for symbole in ("Mf", "b", "d"):
        assert symbole in texte
    assert _sans_chiffres(texte)
    assert svg.count("stroke-width='2.5'/><path") == 3  # 3 plis vus en bout, chacun avec un X


def test_cisaillement():
    r = art_6_5_4.verifier_cisaillement(b=38, d=235, f_v=1.5, plis=1, V_f=5)  # mm ; MPa ; kN
    svg = figure(r)
    texte = _texte(svg)
    for symbole in ("Vf", "b", "d"):
        assert symbole in texte
    assert _sans_chiffres(texte)
    assert svg.count("stroke-width='2.5'/><path") == 1


def test_cisaillement_a_l_entaille():
    # Figure 6.1 : d_n et e
    r = art_6_5_4.verifier_cisaillement_par_fissuration(
        b=38, d=235, d_n=50, e=100, plis=2, V_f=5  # mm ; kN
    )
    svg = figure(r)
    texte = _texte(svg)
    for symbole in ("dn", "e", "Vf", "b", "d"):
        assert symbole in texte
    assert _sans_chiffres(texte)
    assert svg.count("stroke-width='2.5'/><path") == 2


def test_compression_parallele():
    r = art_6_5_5.verifier_compression_parallele_au_fil(
        b=89, d=89, L=3000, L_selon_b=3000, L_selon_d=3000, f_c=11.5, E_05=6500, P_f=10  # mm ; MPa ; kN
    )
    svg = figure(r)
    texte = _texte(svg)
    for symbole in ("Pf", "L", "L(b)", "L(d)", "Ke(b)", "Ke(d)", "b", "d"):
        assert symbole in texte
    assert _sans_chiffres(texte)
    # Entraxes selon b et selon d = L : pas d'appui latéral intermédiaire (2 appuis latéraux en tête seulement)
    assert svg.count("y='105'") == 0


def test_compression_parallele_appui_lateral_intermediaire():
    # L_(b) = 1500 mm < L = 3000 mm : appui latéral intermédiaire dans la vue selon b seulement
    r = art_6_5_5.verifier_compression_parallele_au_fil(
        b=38, d=140, L=3000, L_selon_b=1500, L_selon_d=3000, f_c=11.5, E_05=6500, K_e_selon_b=0.8  # mm ; MPa
    )
    svg = figure(r)
    assert svg.count("y='105'") == 1
    # K_e(b) entré en chiffre est dans la trace (6.5.5.1 : L_e = K_e L = 0.8 x 1500 mm = 1200 mm)
    assert r.etape("L_{e(b)}").valeur == 1200


def test_toutes_les_figures_ont_la_meme_largeur():
    """Même largeur de SVG (360 ou plus) : texte de taille semblable dans la note PDF."""
    import re as _re

    resultats = [
        art_6_5_4.verifier_cisaillement(b=38, d=235, f_v=1.5),
        art_6_5_5.verifier_compression_parallele_au_fil(
            b=89, d=89, L=3000, L_selon_b=3000, L_selon_d=3000, f_c=11.5, E_05=6500
        ),
        _appui(),
        _pres_d_un_appui(),
    ]
    for r in resultats:
        largeur = float(_re.search(r"viewBox='[-\d.]+ [-\d.]+ ([\d.]+)", figure(r)).group(1))
        assert 330 <= largeur <= 390


# --- Figures avant le calcul (retours #9, #13 et #14 : afficher la figure avant d'entrer les valeurs)

def test_figure_avant_le_calcul_de_chaque_verification():
    """Chaque vérification a sa figure sans données : mêmes symboles qu'après le calcul."""
    symboles = {
        "6.5.3": ("Mf", "b", "d"),
        "6.5.4.3": ("Vf", "b", "d"),
        "6.5.4.4": ("dn", "e", "Vf", "b", "d"),
        "6.5.5": ("Pf", "L(b)", "Ke(b)", "L(d)", "Ke(d)", "b", "d"),
        "6.5.6.2": ("Lb", "Rf", "b", "d"),
        "6.5.6.3": ("Lb1", "Lb2", "Pf", "b", "d"),
    }
    for article, attendus in symboles.items():
        svg = figure_avant_le_calcul(article)
        assert svg.startswith("<svg"), article
        texte = _texte(svg)
        for symbole in attendus:
            assert symbole in texte, (article, symbole)
        assert _sans_chiffres(texte, "Lb1", "Lb2"), article


def test_figure_avant_le_calcul_plis():
    # 1 pli par défaut, 3 plis : 3 pièces vues en bout, chacune avec un X
    assert figure_avant_le_calcul("6.5.3").count("stroke-width='2.5'/><path") == 1
    assert figure_avant_le_calcul("6.5.3", plis=3).count("stroke-width='2.5'/><path") == 3


def test_figure_avant_le_calcul_appui_pleine_largeur():
    # Sans b ni b_élément : l'appui a la largeur de la section (40 unités), pas plus étroit (28)
    svg = figure_avant_le_calcul("6.5.6.2")
    assert "width='28'" not in svg


def test_figure_avant_le_calcul_l_b1_sur_le_dessus():
    """Sans longueurs d'appui : L_b1 sur le dessus (charge), comme la figure 6.2 (p. 71)."""
    svg = figure_avant_le_calcul("6.5.6.3")
    assert svg.index(">L<tspan dy='4' font-size='75%'>b1<") < svg.index(">L<tspan dy='4' font-size='75%'>b2<")


def test_figure_avant_le_calcul_couleurs_du_compte():
    svg = figure_avant_le_calcul("6.5.3", principale="#123456", accent="#ABCDEF")
    assert "#123456" in svg and "#ABCDEF" in svg


def test_figure_avant_le_calcul_article_sans_figure():
    assert figure_avant_le_calcul("6.5.8") is None
    assert figure_avant_le_calcul("") is None


# --- Petites icônes des types de calcul (issue #89) ---
from moteur.commun.figures import DOSSIER_ICONES, icone, icone_de_l_article  # noqa: E402


@pytest.mark.parametrize("nom", sorted(p.stem for p in DOSSIER_ICONES.glob("*.svg")))
def test_icone_couleurs_du_compte(nom):
    """Chaque icône prend les deux couleurs du compte ; il ne reste aucune couleur de la marque."""
    svg = icone(nom, principale="#112233", accent="#AA5500")
    assert svg.lstrip().startswith("<svg")
    assert "#112233" in svg and "#AA5500" in svg
    assert "#233614" not in svg.upper() and "#9E5A00" not in svg.upper()


def test_icone_couleurs_inversees():
    """Remplacer la principale par l'accent (et l'inverse) ne mélange pas les deux couleurs."""
    original = icone("traction")
    inverse = icone("traction", principale="#9E5A00", accent="#233614")
    assert original.count("#233614") == inverse.count("#9E5A00") == 1  # 1 trait principal
    assert original.count("#9E5A00") == inverse.count("#233614") == 1  # 1 charge


def test_icone_par_defaut_couleurs_de_la_marque():
    svg = icone("flexion")
    assert svg == (DOSSIER_ICONES / "flexion.svg").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "article, nom",
    [
        ("6.5.3", "flexion"),
        ("6.5.4.3", "cisaillement"),
        ("6.5.4.4", "cisaillement_entaille"),
        ("6.5.5", "compression_parallele"),
        ("6.5.6.2", "compression_perpendiculaire"),
        ("6.5.6.3", "compression_pres_appui"),
        ("6.5.8", "traction"),  # 6.5.8 Résistance à la traction parallèle au fil
        ("6.5.9", "flexion_et_charge_axiale"),  # 6.5.9 Flexion et charge axiale combinées
    ],
)
def test_icone_de_l_article(article, nom):
    assert icone_de_l_article(article) == icone(nom)


def test_article_sans_icone():
    assert icone_de_l_article("6.5.7") is None  # compression oblique : pas d'icône
    assert icone_de_l_article("") is None


def test_icone_absente():
    with pytest.raises(FileNotFoundError):
        icone("n_existe_pas")


def test_icones_des_degres_de_retenue():
    """
    Issue #90 : une icône par ligne du tableau A.4, dans l'ordre de la norme ; le K_e du nom du fichier
    (ex. « 3_ke_1_00.svg ») est celui du tableau, aux couleurs du compte.
    """
    from moteur.commun.figures import icones_des_degres_de_retenue
    from moteur.normes.csa_o86_19.annexe_A_renseignements_supplementaires_et_autres_methodes.art_A_6_bois_de_sciage import (  # noqa: E501
        art_A_6_5_5_1_coefficient_de_longueur_effective as art_A,
    )

    fichiers = sorted((DOSSIER_ICONES / "conditions_d_appui").glob("*_ke_*.svg"))
    assert [f.stem.split("_")[0] for f in fichiers] == ["1", "2", "3", "4", "5", "6", "7"]
    assert [float(f.stem.split("_ke_")[1].replace("_", ".")) for f in fichiers] == [
        K_e for _, K_e in art_A.TABLEAU_A_4
    ]
    icones = icones_des_degres_de_retenue(principale="#112233")
    assert len(icones) == len(art_A.TABLEAU_A_4) == 7
    assert all("#112233" in i and "#233614" not in i for i in icones)


# --- Section de l'élément dans « Matériaux » plutôt que dans chaque onglet (retour #12) ---

from moteur.commun.figures import largeur_de_la_vue, section_de_l_element  # noqa: E402

_AVEC_LA_SECTION_DE_L_ELEMENT = ("6.5.3", "6.5.4.3", "6.5.4.4", "6.5.5")


def _x_du_pli(svg: str) -> int:
    """Nombre de pièces vues en bout (rectangle à trait de 2.5 suivi de son X)."""
    return svg.count("stroke-width='2.5'/><path")


def test_figures_sans_la_section_de_l_element():
    """Sans section : plus de pièce vue en bout, plus de cotes b et d ; l'élévation reste."""
    elevation = {"6.5.3": ("Mf",), "6.5.4.3": ("Vf",), "6.5.4.4": ("dn", "e", "Vf"),
                 "6.5.5": ("Pf", "L(b)", "Ke(b)", "L(d)", "Ke(d)", "L")}
    for article in _AVEC_LA_SECTION_DE_L_ELEMENT:
        avec = figure_avant_le_calcul(article, plis=3)
        sans = figure_avant_le_calcul(article, plis=3, avec_section=False)
        assert _x_du_pli(avec) == 3 and _x_du_pli(sans) == 0, article
        texte = _texte(sans)
        for symbole in elevation[article]:
            assert symbole in texte, (article, symbole)
        # Les cotes b et d sont les dernières étiquettes de la section : absentes sans la section
        assert not re.search(r">[bd]</text>", sans), article
        assert re.search(r">b</text>", avec) and re.search(r">d</text>", avec), article
        assert largeur_de_la_vue(sans) < largeur_de_la_vue(avec), article


def test_figure_avec_la_section_par_defaut():
    """Note PDF : chaque page garde la section (décision de l'utilisateur, retour #12)."""
    r = art_6_5_4.verifier_cisaillement(b=38, d=235, f_v=1.5)
    assert figure(r) == figure(r, avec_section=True)
    assert _x_du_pli(figure(r)) == 1
    assert _x_du_pli(figure(r, avec_section=False)) == 0


def test_figures_de_6_5_6_gardent_la_section_sur_l_appui():
    """6.5.6 : la section montre la largeur d'appui b (6.5.6.2) ; elle reste dans l'onglet."""
    for article in ("6.5.6.2", "6.5.6.3"):
        assert (figure_avant_le_calcul(article, avec_section=False)
                == figure_avant_le_calcul(article)), article
    assert figure(_appui(), avec_section=False) == figure(_appui())


def test_section_de_l_element():
    for plis in (1, 2, 3, 4, 5):
        svg = section_de_l_element(plis)
        assert svg.startswith("<svg") and svg.endswith("</svg>")
        assert _x_du_pli(svg) == plis
        assert _texte(svg) == "bd"  # symboles seulement, aucun chiffre


def test_section_de_l_element_b_sur_toute_la_largeur():
    """b = largeur de l'élément (3.2, p. 35) : la cote b couvre tous les plis."""
    # 1 pli : 40 unités ; 2 plis : 2 x 38 = 76 ; 5 plis : 5 x 16 = 80
    def cote_b(svg: str, x: float) -> float:
        """Longueur de la cote horizontale qui part de x (la cote b), en unités du SVG."""
        fin = re.search(rf"M{x:g} [\d.]+ H([\d.]+) M{x:g} ", svg).group(1)
        return float(fin) - x

    for plis, largeur in ((1, 40), (2, 76), (5, 80)):
        assert cote_b(section_de_l_element(plis), 0) == largeur, plis
    # Les figures des vérifications (traces : b = largeur d'un pli) gardent la cote sur un pli :
    # 2 plis de 38 unités, section à x = 240
    assert cote_b(figure_avant_le_calcul("6.5.3", plis=2), 240) == 38


def test_section_de_l_element_largeur_de_la_vue():
    # 1 pli : 40 unités + 50 (cote d) = 90 ; 2 plis : 2 x 38 = 76 + 50 = 126 ;
    # 5 plis : 76 / 5 = 15.2 < 16, donc 5 x 16 = 80 + 50 = 130
    assert largeur_de_la_vue(section_de_l_element(1)) == 90
    assert largeur_de_la_vue(section_de_l_element(2)) == 126
    assert largeur_de_la_vue(section_de_l_element(5)) == 130


def test_section_de_l_element_couleurs_du_compte():
    svg = section_de_l_element(2, principale="#123456", accent="#ABCDEF")
    assert "#123456" in svg and "#ABCDEF" in svg
    assert "#233614" not in svg and "#9E5A00" not in svg


def test_largeur_de_la_vue():
    assert largeur_de_la_vue("<svg viewBox='-24 0 384 146'></svg>") == 384
    with pytest.raises(ValueError):
        largeur_de_la_vue("<svg></svg>")
