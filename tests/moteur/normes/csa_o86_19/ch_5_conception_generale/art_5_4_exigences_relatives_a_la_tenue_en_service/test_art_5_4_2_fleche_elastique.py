"""Tests de 5.4.2 Flèche élastique : ℓ / 180 (CSA O86:19, p. 44)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_2_fleche_elastique import fleche_elastique_maximale


def test_fleche_maximale():
    # ℓ = 3600 mm : 3600 mm / 180 = 20 mm
    assert fleche_elastique_maximale(3600) == pytest.approx(20.0)
    # ℓ = 5000 mm : 5000 mm / 180 = 27.78 mm
    assert fleche_elastique_maximale(5000) == pytest.approx(27.7778, rel=1e-5)


@pytest.mark.parametrize("ell", [0, -3600])
def test_portee_invalide(ell):
    with pytest.raises(ValueError, match="5.4.2"):
        fleche_elastique_maximale(ell)
