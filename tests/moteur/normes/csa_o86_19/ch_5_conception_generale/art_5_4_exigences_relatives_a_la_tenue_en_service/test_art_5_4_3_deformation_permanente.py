"""Tests de 5.4.3 Déformation permanente : ℓ / 360 (CSA O86:19, p. 44)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_3_deformation_permanente import fleche_elastique_maximale_charges_continues


def test_fleche_maximale_charges_continues():
    # ℓ = 3600 mm : 3600 mm / 360 = 10 mm
    assert fleche_elastique_maximale_charges_continues(3600) == pytest.approx(10.0)
    # ℓ = 4500 mm : 4500 mm / 360 = 12.5 mm
    assert fleche_elastique_maximale_charges_continues(4500) == pytest.approx(12.5)


@pytest.mark.parametrize("l_portee", [0, -1])
def test_portee_invalide(l_portee):
    with pytest.raises(ValueError, match="5.4.3"):
        fleche_elastique_maximale_charges_continues(l_portee)


# --- Vérification : flèche entrée par l'ingénieur (réponse de l'utilisateur, 28 novembre 2026) ---
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_3_deformation_permanente import (  # noqa: E402, E501
    verifier_deformation_permanente,
)


def test_verifier_deformation_permanente():
    # ℓ = 3600 mm : ℓ / 360 = 10 mm ; 9 mm / 10 mm = 0,90
    r = verifier_deformation_permanente(3600, 9)
    assert r.etapes[0].valeur == 10
    assert r.verification.ratio == pytest.approx(0.90)
    assert r.verification.respecte and r.verification.article == "5.4.3"
    assert verifier_deformation_permanente(3600, 10).verification.respecte  # 1,00 au seuil
    assert not verifier_deformation_permanente(3600, 10.5).verification.respecte  # 1,05
    with pytest.raises(ValueError):
        verifier_deformation_permanente(3600, -0.1)
