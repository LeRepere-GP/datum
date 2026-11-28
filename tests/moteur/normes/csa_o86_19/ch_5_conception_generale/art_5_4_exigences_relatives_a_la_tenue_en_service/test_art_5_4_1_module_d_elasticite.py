"""Tests de 5.4.1 Module d'élasticité, E_S = E (K_SE K_T) (CSA O86:19, p. 44)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_1_module_d_elasticite import E_S


def test_E_S_sec_non_traite():
    # E = 9500 MPa, K_SE = 1.00, K_T = 1.00 : E_S = 9500 MPa
    assert E_S(9500, 1.00, 1.00) == pytest.approx(9500)


def test_E_S_humide_traite():
    # E = 9500 MPa, K_SE = 0.94 (tableau 6.10, humide), K_T = 0.95 :
    # 9500 MPa x (0.94 x 0.95) = 9500 x 0.893 = 8483.5 MPa
    assert E_S(9500, 0.94, 0.95) == pytest.approx(8483.5)


@pytest.mark.parametrize("E, K_SE, K_T", [(0, 1, 1), (9500, 0, 1), (9500, 1, -0.5)])
def test_E_S_valeurs_invalides(E, K_SE, K_T):
    with pytest.raises(ValueError, match="5.4.1"):
        E_S(E, K_SE, K_T)
