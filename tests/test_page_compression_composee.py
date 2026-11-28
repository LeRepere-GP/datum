"""
Page Bois de sciage, onglet Compression parallèle au fil : éléments composés de plusieurs plis
(6.5.5.4, issue #32).
"""

from unittest import mock

from tests.test_acces import _connecte


def _element_compose(at, plis: int, assemblage: str | None = None):
    """
    2x6 S-P-F n° 1/n° 2 (plis de 38 mm x 140 mm), L = 3000 mm, L_(b) = 1500 mm, L_(d) = 3000 mm,
    P_f = 5 kN. La pièce est entrée dans la boîte « Pièce » (datum-retours #20), ex. « 3 2x6 ».
    """
    [t for t in at.text_input if t.key == "piece"][0].set_value(f"{plis} 2x6").run()
    if assemblage is not None:
        [r for r in at.radio if r.key == "cpa_assemblage"][0].set_value(assemblage).run()
    [n for n in at.text_input if n.key == "cpa_L"][0].set_value("3000 mm")
    [n for n in at.text_input if n.key == "cpa_L_selon_b"][0].set_value("1500 mm")
    [n for n in at.text_input if n.key == "cpa_L_selon_d"][0].set_value("3000 mm")
    at.run()
    [n for n in at.text_input if n.key == "cpa_pf"][0].set_value("5.0")  # kN
    return at.run()


def _p_r(at) -> list[str]:
    """P_r affichée, partie métrique seulement (ex. « $P_r = 109 kN$ »)."""
    import re
    return [
        re.sub(r"^\$P_r = \\text\{(.*?) \(.*\)\}\$$", r"$P_r = \1$", m.value)
        for m in at.markdown if m.value.startswith("$P_r")
    ]


def test_element_compose_boulonne():
    # 3-2x6 boulonnés : P_r = min(116.3 kN ; 108.6 kN) = 108.6 kN -> 109 kN (3 chiffres significatifs).
    # Calcul à la main : tests du moteur (test_3_plis_boulonnes_selon_d_gouverne).
    at = _element_compose(_connecte("admin", "mot-admin"), 3, "boulons")
    assert not at.exception
    assert not [w for w in at.warning if "plusieurs plis" in w.value]  # plus « fonctionnalité à venir »
    assert _p_r(at) == ["$P_r = 109 kN$"]
    assert any("respecté" in s.value for s in at.success)
    # Exigences d'assemblage en notes, toujours visibles (décision de l'utilisateur)
    notes = [w.value for w in at.warning if w.value.startswith("**Notes (6.5.5.4)**")]
    assert len(notes) == 1
    assert "Datum ne vérifie pas" in notes[0] and "6.5.5.4.3 a)" in notes[0]
    # Détail de la trace dans « Voir plus »
    assert any(m.value.startswith("6.5.5.4.6 ") for m in at.markdown)


def test_element_compose_cloue_par_defaut():
    # 2-2x6 cloués (choix par défaut) : selon b, massif = 9.2 MPa x 76 mm x 140 mm x K_Zc x K_C
    # C_C(b) = 1500 mm / 76 mm = 19.737 ; K_Zc = 1.26702 ;
    # K_C = [1 + 11.5 x 1.26702 x 19.737^3 / 227 500]^-1 = [1 + 0.492416]^-1 = 0.670054
    # massif : 9.2 MPa x 10 640 mm² x 1.26702 x 0.670054 = 83 106 N ; x 0.60 = 49 864 N
    # plis : C_C = 1500 mm / 38 mm = 39.474 ; P_r d'un pli = 12 620 N ; 2 plis : 25 240 N
    # P_r(b) = 49 864 N ; P_r(d) = 9.2 MPa x 10 640 mm² x 1.1704 x 0.63206 = 72 41x N
    # P_r = 49.9 kN
    at = _element_compose(_connecte("admin", "mot-admin"), 2)
    assert not at.exception
    assert [r for r in at.radio if r.key == "cpa_assemblage"][0].value == "clous"
    assert _p_r(at) == ["$P_r = 49.9 kN$"]


def test_element_simple_inchange():
    # 1 pli : pas de choix d'assemblage ni de notes ; même calcul qu'avant (6.5.5)
    at = _element_compose(_connecte("admin", "mot-admin"), 1)
    assert not at.exception
    assert not [r for r in at.radio if r.key == "cpa_assemblage"]
    assert not [w for w in at.warning if w.value.startswith("**Notes")]


def test_element_compose_dans_la_note_pdf():
    from moteur.commun import note_de_calcul

    with mock.patch.object(note_de_calcul, "produire_pdf", return_value=b"%PDF") as produire:
        at = _element_compose(_connecte("admin", "mot-admin"), 3, "anneaux_fendus")
    assert not at.exception
    traces = [r[1] for r in produire.call_args.args[0]]
    compose = [t for t in traces if t.article == "6.5.5.4"]
    assert len(compose) == 1 and compose[0].notes

