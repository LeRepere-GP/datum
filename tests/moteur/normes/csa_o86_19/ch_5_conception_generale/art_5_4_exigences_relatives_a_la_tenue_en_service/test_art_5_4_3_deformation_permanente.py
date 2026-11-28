"""Tests de 5.4.3 Déformation permanente : ℓ / 360 (CSA O86:19, p. 44)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_3_deformation_permanente import fleche_elastique_maximale_charges_continues


def test_fleche_maximale_charges_continues():
    # ℓ = 3600 mm : 3600 mm / 360 = 10 mm
    assert fleche_elastique_maximale_charges_continues(3600) == pytest.approx(10.0)
    # ℓ = 4500 mm : 4500 mm / 360 = 12.5 mm
    assert fleche_elastique_maximale_charges_continues(4500) == pytest.approx(12.5)


@pytest.mark.parametrize("ell", [0, -1])
def test_portee_invalide(ell):
    with pytest.raises(ValueError, match="5.4.3"):
        fleche_elastique_maximale_charges_continues(ell)
