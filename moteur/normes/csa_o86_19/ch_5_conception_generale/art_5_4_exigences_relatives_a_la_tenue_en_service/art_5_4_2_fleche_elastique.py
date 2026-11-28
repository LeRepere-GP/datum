"""
CSA O86:19 - 5.4.2 Flèche élastique (p. 44).

« La flèche élastique des éléments de charpente soumis à des combinaisons de charges, dans le calcul aux
états limites de tenue en service, ne doit pas dépasser 1/180 de la portée. Dans le cas des éléments qui
présentent une contreflèche au moins égale à la flèche due aux charges permanentes, la flèche
supplémentaire due aux surcharges et aux charges dues à la neige et au vent ne doit pas dépasser
1/180 de la portée. »
(« The elastic deflection of structural members under the load combinations for serviceability limit
states shall not exceed 1/180 of the span. [...] »)

La portée a le symbole ℓ à 3.2 (« ℓ = portée, mm », p. 37). En Python, ℓ est lu comme la lettre l
(normalisation Unicode NFKC) : le code l'écrit donc `ell` (question posée à l'utilisateur dans la PR).

La flèche elle-même n'est pas calculée ici (pas de formule dans la norme) : elle vient de l'analyse de
l'ingénieur. La note de 5.4.2 renvoie à A.5.4.2 (systèmes à ossature en bois).
"""

FRACTION_DE_LA_PORTEE = 180  # 5.4.2 : flèche <= 1/180 de la portée


def fleche_elastique_maximale(ell: float) -> float:
    """
    5.4.2 Flèche élastique maximale sous les combinaisons de charges de tenue en service : ℓ / 180.

    La même limite s'applique à la flèche supplémentaire (surcharges, neige et vent) d'un élément dont
    la contreflèche est au moins égale à la flèche due aux charges permanentes.

    Args:
        ell (float): ℓ, portée, mm (3.2).

    Returns:
        float: Flèche élastique maximale, mm.

    Raises:
        ValueError: Si la portée n'est pas positive.
    """
    if ell <= 0:
        raise ValueError("La portée ℓ doit être positive (5.4.2).")
    return ell / FRACTION_DE_LA_PORTEE
