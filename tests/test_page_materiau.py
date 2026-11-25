"""
Page Bois de sciage, section Matériau : dimensions nettes (tableau A.3) et catégorie (6.2.2,
tableau 6.3), calculées par le nouveau moteur (feuille de route, étape 7).
"""

from tests.test_acces import _connecte


def _choisir(widgets, debut):
    return next(w for w in widgets if w.label.startswith(debut))


def _dimensions(at):
    return [m.value for m in at.metric][:2]


def _categorie(at):
    return at.text[0].value


def test_2x6_sec_par_defaut():
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    assert _dimensions(at) == ["38 mm (1 1/2 po)", "140 mm (5 1/2 po)"]
    assert _categorie(at) == "Montants, solives et madriers"  # tableau 6.4
    # 38 x 140 mm : 140 mm > 89 mm, pas de choix « Charpente légère » (tableau 6.3)
    assert "Charpente légère (Const., Std.)" not in [t.label for t in at.toggle]


def test_2x4_charpente_legere_au_choix():
    at = _connecte("admin", "mot-admin")
    _choisir(at.selectbox, "Hauteur nominale").set_value(4).run()
    assert _categorie(at) == "Montants, solives et madriers"  # tableau 6.4 par défaut (issue #34)
    _choisir(at.toggle, "Charpente légère").set_value(True).run()
    assert not at.exception
    assert _categorie(at) == "Charpente légère"  # tableau 6.5


def test_gros_bois_vert():
    at = _connecte("admin", "mot-admin")
    _choisir(at.selectbox, "Largeur nominale").set_value(6).run()
    _choisir(at.selectbox, "Hauteur nominale").set_value(8).run()
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "184 mm (7 1/4 po)"]  # 6x8 sec
    _choisir(at.toggle, "Bois vert").set_value(True).run()
    # Gros bois vert (tableau A.3) : 140 x 191 mm ; 191 mm - 140 mm = 51 mm -> poteaux
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "191 mm (7 1/2 po)"]
    assert _categorie(at) == "Poteaux et bois carrés"
    _choisir(at.selectbox, "Hauteur nominale").set_value(9).run()
    # 9 po : gros bois vert seulement, 216 mm ; 216 mm - 140 mm = 76 mm > 51 mm -> poutres
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "216 mm (8 1/2 po)"]
    assert _categorie(at) == "Poutres et longerons"


def test_9_po_sec_refuse():
    at = _connecte("admin", "mot-admin")
    _choisir(at.selectbox, "Largeur nominale").set_value(6).run()
    _choisir(at.selectbox, "Hauteur nominale").set_value(9).run()
    assert not at.exception
    assert "seulement pour le gros bois vert" in at.error[0].value


def test_plus_de_412_mm_avertissement():
    at = _connecte("admin", "mot-admin")
    _choisir(at.toggle, "Dimensions brutes").set_value(True).run()
    _choisir(at.number_input, "Hauteur réelle").set_value(16.0).run()  # 16 po x 25.4 mm/po = 406.4 mm -> 406 mm <= 412 mm
    assert "fournisseurs" not in " ".join(w.value for w in at.warning)
    _choisir(at.number_input, "Hauteur réelle").set_value(16.25).run()  # 16.25 po x 25.4 mm/po = 412.75 mm -> 413 mm > 412 mm
    assert not at.exception
    assert at.warning[0].value == "Valider la disponibilité du bois chez les fournisseurs."
    assert _categorie(at) == "Poutres et longerons"  # comportement conservé
