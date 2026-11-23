"""Page Bois de sciage : tableau « Résumé » des vérifications faites (issue #85)."""

from tests.test_acces import _connecte


def _resume(at):
    return [m.value for m in at.markdown if m.value.startswith("| Vérification")]


def test_pas_de_resume_sans_verification():
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    assert _resume(at) == []


def test_resume_de_deux_verifications():
    at = _connecte("admin", "mot-admin")
    for cle, valeur in (("cp_support_length", 89.0), ("cp_rf", 5.0)):  # mm ; kN
        [n for n in at.number_input if n.key == cle][0].set_value(valeur)
    [n for n in at.number_input if n.label.startswith("$Vf")][0].set_value(1.0)  # kN
    at.run()
    assert not at.exception
    (tableau,) = _resume(at)
    lignes = tableau.splitlines()[2:]
    assert len(lignes) == 2  # cisaillement (6.5.4.3) et compression perpendiculaire (6.5.6.2)
    # Une seule ligne en gras : celle qui gouverne
    assert sum(l.count("**") > 0 for l in lignes) == 1
    assert all("✔ Conforme" in l for l in lignes)
    assert any("Résumé" == s.value for s in at.subheader)
