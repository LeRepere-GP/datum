"""Tests du résumé des vérifications (moteur/commun/resume.py, issue #85)."""

import math

from moteur.commun.resultat import Resultat, Verification
from moteur.commun.resume import resume


def trace(titre, article, charge, resistance, symboles=("P_f", "P_r")):
    """Trace minimale avec sa vérification finale (ratio calculé à la main dans chaque test)."""
    ratio = charge / resistance if resistance > 0 else math.inf
    return Resultat(
        "CSA O86:19", article, titre,
        verification=Verification(
            "5.1.2", symboles[0], charge, symboles[1], resistance, ratio, ratio <= 1.0, "kN", "force"
        ),
    )


def test_une_ligne_par_verification_faite():
    # Cisaillement : 5 kN / 10 kN = 0.50 ; compression : 8 kN / 10 kN = 0.80 (gouverne)
    lignes = resume([
        ("P-1", trace("Cisaillement", "6.5.4.3", 5.0, 10.0, ("V_f", "V_r"))),
        ("P-1", trace("Compression parallèle au fil", "6.5.5", 8.0, 10.0)),
    ])
    assert [l.titre for l in lignes] == ["Cisaillement", "Compression parallèle au fil"]  # ordre reçu
    l = lignes[0]
    assert (l.element, l.article, l.symbole_charge, l.symbole_resistance) == ("P-1", "6.5.4.3", "V_f", "V_r")
    assert (l.charge, l.resistance, l.unite, l.grandeur) == (5.0, 10.0, "kN", "force")
    assert l.ratio == 0.5 and l.respecte
    assert [l.gouverne for l in lignes] == [False, True]


def test_trace_sans_verification_ignoree():
    # Charge pondérée pas encore entrée : pas de ligne
    sans = Resultat("CSA O86:19", "6.5.3", "Flexion")
    lignes = resume([("P-1", sans, True), ("P-1", trace("Compression", "6.5.5", 2.0, 10.0), False)])
    assert [l.titre for l in lignes] == ["Compression"]
    assert lignes[0].gouverne  # seule vérification : elle gouverne


def test_aucune_verification():
    assert resume([]) == []
    assert resume([("P-1", Resultat("CSA O86:19", "6.5.3", "Flexion"))]) == []


def test_ratios_egaux_la_premiere_gouverne():
    # 10 kN / 10 kN = 1.00 (au seuil : respecté) dans les deux cas
    lignes = resume([("A", trace("Un", "6.5.5", 10.0, 10.0)), ("B", trace("Deux", "6.5.6", 10.0, 10.0))])
    assert [l.gouverne for l in lignes] == [True, False]
    assert all(l.respecte for l in lignes)


def test_depassee_et_resistance_nulle():
    # 12 kN / 10 kN = 1.20 (dépassé) ; résistance nulle : ratio infini, qui gouverne
    lignes = resume([
        ("A", trace("Dépassée", "6.5.5", 12.0, 10.0)),
        ("A", trace("Nulle", "6.5.6", 1.0, 0.0)),
    ])
    assert not lignes[0].respecte and math.isclose(lignes[0].ratio, 1.2)
    assert math.isinf(lignes[1].ratio) and lignes[1].gouverne and not lignes[1].respecte
