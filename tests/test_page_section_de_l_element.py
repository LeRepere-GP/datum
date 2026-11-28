"""
Page Bois de sciage : section de l'élément (b, d, plis) dans « Matériaux », pas dans chaque onglet de
calcul (retour LeRepere-GP/datum-retours#12).
"""

import base64
import re

from tests.test_acces import _connecte


def _svg_affiches(noeud) -> list[str]:
    """SVG bruts de toutes les images de la page, dans l'ordre d'affichage."""
    svgs = []
    for e in getattr(noeud, "children", {}).values():
        if getattr(e, "type", None) == "image":
            for image in e.proto.imgs:
                if image.url.startswith("data:image/svg+xml;base64,"):
                    svgs.append(base64.b64decode(image.url.split(",", 1)[1]).decode())
        svgs += _svg_affiches(e)
    return svgs


def _texte(svg: str) -> str:
    return re.sub(r"<[^>]+>", "", svg).replace("​", "")


def _sections(svgs: list[str]) -> list[str]:
    """La section de « Matériaux » : seulement les cotes b et d."""
    return [s for s in svgs if _texte(s) == "bd"]


def _x_du_pli(svg: str) -> int:
    return svg.count("stroke-width='2.5'/><path")


def test_section_dans_materiaux_seulement():
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    svgs = _svg_affiches(at._tree)
    sections = _sections(svgs)
    assert len(sections) == 1 and _x_du_pli(sections[0]) == 1
    # Flexion, cisaillement, entaille et compression parallèle : élévation seulement
    for symbole in ("Mf", "dn", "Ke(b)"):
        figure = next(s for s in svgs if symbole in _texte(s))
        assert _x_du_pli(figure) == 0, symbole
    cisaillement = next(s for s in svgs if "Vf" in _texte(s) and "dn" not in _texte(s))
    assert _x_du_pli(cisaillement) == 0
    # 6.5.6.2 et 6.5.6.3 gardent la section sur l'appui (largeur d'appui b)
    for figure in (s for s in svgs if "Lb" in _texte(s)):
        assert _x_du_pli(figure) == 1


def test_section_suit_le_nombre_de_plis():
    at = _connecte("admin", "mot-admin")
    [t for t in at.text_input if t.key == "piece"][0].set_value("3 2x6").run()  # 3 plis de 2x6 (datum-retours #20)
    assert not at.exception
    sections = _sections(_svg_affiches(at._tree))
    assert len(sections) == 1 and _x_du_pli(sections[0]) == 3


def test_figures_apres_le_calcul_sans_section():
    """Une fois la vérification faite (V_f entré), la figure tirée de la trace reste sans section."""
    at = _connecte("admin", "mot-admin")
    [n for n in at.text_input if n.label == "$V_f: (kN)$"][0].set_value("5.0").run()  # kN
    assert not at.exception
    svgs = _svg_affiches(at._tree)
    cisaillement = next(s for s in svgs if "Vf" in _texte(s) and "dn" not in _texte(s))
    assert _x_du_pli(cisaillement) == 0
    assert len(_sections(svgs)) == 1


def _resume(at):
    return [m.value for m in at.markdown if m.value.startswith("| Vérification")]


def test_element_compose_trace_avec_la_largeur_totale():
    """
    Issue #95 : la page passe b = largeur de l'élément (3.2), tous les plis compris, au nouveau moteur.
    Avec 2 plis : V_r = 0.9 x 1.5 MPa x 1.10 x 2/3 x (76 mm x 140 mm) x 1.4 = 14 747 N -> 14.7 kN, dans
    l'onglet et dans le Résumé (même trace, issue #98). Avec la largeur d'un pli seulement (38 mm), la
    trace donnerait environ la moitié (7.4 kN).
    """
    at = _connecte("admin", "mot-admin")
    [t for t in at.text_input if t.key == "piece"][0].set_value("2 2x6").run()  # 2 plis de 2x6 (datum-retours #20)
    [n for n in at.text_input if n.label == "$V_f: (kN)$"][0].set_value("1.0").run()  # kN
    assert not at.exception
    v_r_affiche = next(m.value for m in at.markdown if m.value.startswith("$V_r = "))
    v_r_affiche = float(v_r_affiche.removeprefix("$V_r = \\text{").split(" kN")[0])  # « 14.7 kN (3 310 lb) »
    (tableau,) = _resume(at)
    ligne = next(l for l in tableau.splitlines() if "6.5.4.3" in l)
    v_r_trace = float(re.search(r"\$V_r\$ = ([\d.]+) kN", ligne).group(1))
    assert v_r_affiche == v_r_trace == 14.7  # kN
