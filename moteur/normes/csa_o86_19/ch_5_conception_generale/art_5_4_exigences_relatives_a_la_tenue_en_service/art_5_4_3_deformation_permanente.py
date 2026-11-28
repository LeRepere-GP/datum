"""
CSA O86:19 - 5.4.3 Déformation permanente (p. 44).

« Les éléments de charpente qui supportent des charges de durée d'application continue doivent être
conçus de manière à limiter les déformations permanentes. Faute d'une méthode d'évaluation plus précise
des limites acceptables pour les flèches, une flèche égale au 1/360 de la portée doit être considérée
comme étant la limite supérieure à ne pas dépasser dans le calcul de la flèche élastique due aux
combinaisons de charges de durée d'application continue. »
(« [...] an upper limit of 1/360 of the span shall be imposed on the elastic deflection due to long-term
service load combinations. »)

La portée ℓ (3.2, p. 37) est écrite `ell` dans le code (voir art_5_4_2_fleche_elastique.py).
"""

FRACTION_DE_LA_PORTEE = 360  # 5.4.3 : flèche (charges continues) <= 1/360 de la portée


def fleche_elastique_maximale_charges_continues(ell: float) -> float:
    """
    5.4.3 Flèche élastique maximale sous les combinaisons de charges de durée d'application continue :
    ℓ / 360 (faute d'une méthode d'évaluation plus précise).

    Args:
        ell (float): ℓ, portée, mm (3.2).

    Returns:
        float: Flèche élastique maximale, mm.

    Raises:
        ValueError: Si la portée n'est pas positive.
    """
    if ell <= 0:
        raise ValueError("La portée ℓ doit être positive (5.4.3).")
    return ell / FRACTION_DE_LA_PORTEE
