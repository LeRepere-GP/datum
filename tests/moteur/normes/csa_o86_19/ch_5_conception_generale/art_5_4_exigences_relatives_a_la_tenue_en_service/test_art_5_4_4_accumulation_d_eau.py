"""Tests de 5.4.4 Accumulation d'eau : ΣΔ / w < 65 (CSA O86:19, p. 45)."""

import pytest

from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_4_accumulation_d_eau import (
    accumulation_d_eau_sans_analyse_rationnelle,
    somme_Delta_sur_w,
)


def test_somme_Delta_sur_w():
    # Platelage 10 mm + poutre secondaire 30 mm + poutre principale 40 mm = 80 mm ;
    # w = 2.0 kN/m² : 80 mm / 2.0 kN/m² = 40
    assert somme_Delta_sur_w([10, 30, 40], 2.0) == pytest.approx(40.0)


def test_condition_satisfaite():
    # 40 < 65 : pas d'analyse rationnelle exigée
    assert accumulation_d_eau_sans_analyse_rationnelle([10, 30, 40], 2.0) is True


def test_condition_au_seuil_non_satisfaite():
    # 130 mm / 2.0 kN/m² = 65 : inégalité stricte, 65 < 65 est faux
    assert somme_Delta_sur_w([130], 2.0) == 65
    assert accumulation_d_eau_sans_analyse_rationnelle([130], 2.0) is False


def test_condition_non_satisfaite():
    # 100 mm + 50 mm = 150 mm ; 150 mm / 2.0 kN/m² = 75 > 65
    assert accumulation_d_eau_sans_analyse_rationnelle([100, 50], 2.0) is False


def test_fleches_nulles():
    assert somme_Delta_sur_w([0, 0], 1.5) == 0


@pytest.mark.parametrize("Delta, w", [([10], 0), ([10], -1), ([], 2.0), ([10, -5], 2.0)])
def test_valeurs_invalides(Delta, w):
    with pytest.raises(ValueError, match="5.4.4"):
        somme_Delta_sur_w(Delta, w)
