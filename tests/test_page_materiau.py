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


def _piece(at, texte):
    """Entre le texte de la boîte « Pièce » (datum-retours #20)."""
    [t for t in at.text_input if t.key == "piece"][0].set_value(texte).run()
    assert not at.exception
    return at


def _compris(at):
    """Ligne « Compris : ... » affichée sous la boîte « Pièce »."""
    return next(c.value for c in at.caption if c.value.startswith("Compris : "))


def test_2x6_compris_sous_la_boite():
    at = _connecte("admin", "mot-admin")
    # 2x6 sec nominal (tableau A.3) : 38 x 140 mm ; 38 mm / 25.4 mm/po = 1.496 po -> 1 1/2 po
    assert _compris(at) == (
        "Compris : 2x6, sec, dimensions nominales (tableau A.3) : "
        "b = 38 mm (1 1/2 po), d = 140 mm (5 1/2 po)."
    )
    # Les anciens champs sont retirés (décision de l'utilisateur, #20)
    assert not [t for t in at.toggle if t.label in ("Bois vert", "Dimensions brutes")]
    assert not [s for s in at.selectbox if "nominale" in s.label]
    assert not [r for r in at.radio if r.label.startswith("Élément composé")]


def test_2x4_charpente_legere_au_choix():
    at = _piece(_connecte("admin", "mot-admin"), "2x4")
    assert _dimensions(at) == ["38 mm (1 1/2 po)", "89 mm (3 1/2 po)"]
    assert _categorie(at) == "Montants, solives et madriers"  # tableau 6.4 par défaut (issue #34)
    _choisir(at.toggle, "Charpente légère").set_value(True).run()
    assert not at.exception
    assert _categorie(at) == "Charpente légère"  # tableau 6.5


def test_gros_bois_vert():
    at = _piece(_connecte("admin", "mot-admin"), "6x8")
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "184 mm (7 1/4 po)"]  # 6x8 sec
    _piece(at, "6x8 vert")
    # Gros bois vert (tableau A.3) : 140 x 191 mm ; 191 mm - 140 mm = 51 mm -> poteaux
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "191 mm (7 1/2 po)"]
    assert _categorie(at) == "Poteaux et bois carrés"
    assert "gros bois vert" in _compris(at)
    _piece(at, "6x9 vert")
    # 9 po : gros bois vert seulement, 216 mm ; 216 mm - 140 mm = 76 mm > 51 mm -> poutres
    assert _dimensions(at) == ["140 mm (5 1/2 po)", "216 mm (8 1/2 po)"]
    assert _categorie(at) == "Poutres et longerons"


def test_9_po_sec_lu_comme_brut():
    # 9 po sec : absent du tableau A.3 (gros bois vert seulement) -> dimensions brutes (réponse de
    # l'utilisateur, #20) : 6 po -> 152 mm, 9 po -> 229 mm (colonne « dry_brut » de la base de données)
    at = _piece(_connecte("admin", "mot-admin"), "6x9")
    assert not at.error
    assert _dimensions(at) == ["152 mm (6 po)", "229 mm (9 po)"]
    assert "dimensions brutes" in _compris(at)


def test_plusieurs_plis():
    at = _piece(_connecte("admin", "mot-admin"), "3-2x10")
    # 3 plis de 2x10 : b = 3 x 38 mm = 114 mm ; 114 mm / 25.4 mm/po = 4.488 po -> 4 1/2 po ; d = 235 mm
    assert _dimensions(at) == ["3*38 = 114 mm (4 1/2 po)", "235 mm (9 1/4 po)"]
    assert _compris(at).startswith("Compris : 3 plis de 2x10, sec, dimensions nominales (tableau A.3) : b = 3 × 38")


def test_millimetres_dimensions_reelles():
    at = _piece(_connecte("admin", "mot-admin"), "89 x 140 mm")
    assert _dimensions(at) == ["89 mm (3 1/2 po)", "140 mm (5 1/2 po)"]
    assert "dimensions réelles" in _compris(at)


def test_texte_refuse():
    at = _piece(_connecte("admin", "mot-admin"), "2x6 spf")
    assert "« 2x6 spf » : le mot « spf » n'est pas reconnu" in at.error[0].value
    # Rien n'est calculé après un refus : pas de catégorie ni de dimensions
    assert not at.metric
    _piece(at, "")
    assert "entrez la pièce" in at.error[0].value


def test_plus_de_412_mm_avertissement():
    at = _connecte("admin", "mot-admin")
    _piece(at, "1 1/2 x 16")  # 16 po brut (1 1/2 po non entier -> brut) : 406 mm (dry_brut) <= 412 mm
    assert _dimensions(at)[1] == "406 mm (16 po)"
    assert "fournisseurs" not in " ".join(w.value for w in at.warning)
    _piece(at, "1 1/2 x 16 1/4")  # 16.25 po x 25.4 mm/po = 412.75 mm -> 413 mm > 412 mm
    assert at.warning[0].value == "Valider la disponibilité du bois chez les fournisseurs."
    assert _categorie(at) == "Poutres et longerons"  # comportement conservé
