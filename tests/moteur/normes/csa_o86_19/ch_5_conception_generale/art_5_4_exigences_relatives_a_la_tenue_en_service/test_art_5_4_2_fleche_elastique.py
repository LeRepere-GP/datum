"""Tests de 5.4.2 Flèche élastique : ℓ / 180 (CSA O86:19, p. 44)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_2_fleche_elastique import fleche_elastique_maximale


def test_fleche_maximale():
    # ℓ = 3600 mm : 3600 mm / 180 = 20 mm
    assert fleche_elastique_maximale(3600) == pytest.approx(20.0)
    # ℓ = 5000 mm : 5000 mm / 180 = 27.78 mm
    assert fleche_elastique_maximale(5000) == pytest.approx(27.7778, rel=1e-5)


@pytest.mark.parametrize("l_portee", [0, -3600])
def test_portee_invalide(l_portee):
    with pytest.raises(ValueError, match="5.4.2"):
        fleche_elastique_maximale(l_portee)


# --- Vérification : flèche entrée par l'ingénieur (réponse de l'utilisateur, 28 novembre 2026) ---
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_2_fleche_elastique import (  # noqa: E402, E501
    verifier_fleche_elastique,
)


def test_verifier_fleche_elastique():
    # ℓ = 3600 mm : ℓ / 180 = 20 mm
    r = verifier_fleche_elastique(3600, 15)
    assert r.etapes[0].valeur == 20
    assert r.verification.ratio == pytest.approx(0.75)  # 15 mm / 20 mm
    assert r.verification.respecte and r.verification.article == "5.4.2"
    # Au seuil : 20 mm / 20 mm = 1,00, respecté (« ne doit pas dépasser »)
    assert verifier_fleche_elastique(3600, 20).verification.respecte
    # 21 mm / 20 mm = 1,05 : dépassé
    depasse = verifier_fleche_elastique(3600, 21).verification
    assert depasse.ratio == pytest.approx(1.05) and not depasse.respecte
    # Flèche nulle : ratio 0
    assert verifier_fleche_elastique(3600, 0).verification.ratio == 0
    with pytest.raises(ValueError):
        verifier_fleche_elastique(3600, -1)
    with pytest.raises(ValueError):
        verifier_fleche_elastique(0, 5)
