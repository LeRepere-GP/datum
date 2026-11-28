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
(normalisation Unicode NFKC) : le code l'écrit donc `l_portee` (réponse de l'utilisateur, 28 novembre
2026, PR #119) ; l'affichage garde ℓ.

La flèche elle-même n'est pas calculée ici (pas de formule dans la norme) : elle vient de l'analyse de
l'ingénieur, qui l'entre (réponse de l'utilisateur, 28 novembre 2026, PR #119). La flèche n'a pas de
symbole à 5.4.2 (Δ est défini seulement dans 5.4.4) : elle n'en a pas ici (règle de la PR #87). La note de 5.4.2 renvoie à A.5.4.2 (systèmes à ossature en bois).
"""

from moteur.commun.registre import enregistrer
from moteur.commun.resultat import Donnee, Etape, Resultat, Verification
from moteur.normes.csa_o86_19 import NORME

EDITION = "csa_o86_19"
FRACTION_DE_LA_PORTEE = 180  # 5.4.2 : flèche <= 1/180 de la portée


def fleche_elastique_maximale(l_portee: float) -> float:
    """
    5.4.2 Flèche élastique maximale sous les combinaisons de charges de tenue en service : ℓ / 180.

    La même limite s'applique à la flèche supplémentaire (surcharges, neige et vent) d'un élément dont
    la contreflèche est au moins égale à la flèche due aux charges permanentes.

    Args:
        l_portee (float): ℓ, portée, mm (3.2).

    Returns:
        float: Flèche élastique maximale, mm.

    Raises:
        ValueError: Si la portée n'est pas positive.
    """
    if l_portee <= 0:
        raise ValueError("La portée ℓ doit être positive (5.4.2).")
    return l_portee / FRACTION_DE_LA_PORTEE


def verifier_fleche_contre_la_limite(fleche: float, fleche_maximale: float, article: str) -> Verification:
    """
    5.4.2 et 5.4.3 La flèche élastique ne doit pas dépasser la limite (« ne doit pas dépasser »).

    Ratio = flèche / flèche maximale ; un ratio exactement égal à 1,00 respecte la limite. Ce n'est pas un
    état limite ultime (5.1.2) : la flèche n'est pas une charge pondérée, d'où cette fonction séparée.

    Args:
        fleche (float): Flèche élastique entrée par l'ingénieur, mm (>= 0).
        fleche_maximale (float): ℓ / 180 (5.4.2) ou ℓ / 360 (5.4.3), mm.
        article (str): "5.4.2" ou "5.4.3".

    Returns:
        Verification: Ratio et état (respecté ou dépassé), en mm.

    Raises:
        ValueError: Si la flèche est négative.
    """
    if fleche < 0:
        raise ValueError(f"La flèche doit être positive ou nulle (calculs de base, {article}).")
    ratio = fleche / fleche_maximale
    return Verification(
        article=article, symbole_charge="", charge=fleche, symbole_resistance="", resistance=fleche_maximale,
        ratio=ratio, respecte=ratio <= 1, unite="mm", grandeur="dimension",
    )


@enregistrer(EDITION, "5.4.2", "Flèche élastique")
def verifier_fleche_elastique(l_portee: float, fleche: float) -> Resultat:
    """
    5.4.2 Flèche élastique sous les combinaisons de charges de tenue en service : flèche <= ℓ / 180.

    La flèche vient de l'analyse de l'ingénieur (pas de formule de flèche dans la norme).

    Args:
        l_portee (float): ℓ, portée, mm (3.2). Affichage : ℓ.
        fleche (float): Flèche élastique sous les combinaisons de charges de tenue en service, mm.

    Returns:
        Resultat: Trace : ℓ / 180, puis la flèche comparée à cette limite (en mm).

    Raises:
        ValueError: Si la portée n'est pas positive ou si la flèche est négative.
    """
    r = Resultat(NORME, "5.4.2", "Flèche élastique")
    r.ajouter_donnee(Donnee(r"\ell", "Portée", l_portee, "mm", "longueur"))
    r.ajouter_donnee(Donnee("", "Flèche élastique (combinaisons de charges de tenue en service)", fleche,
                            "mm", "dimension"))  # pas de symbole à 5.4.2
    maximale = r.ajouter_etape(Etape(
        "5.4.2", "Flèche élastique maximale", "", r"\ell / 180", rf"{l_portee:g} / 180",
        fleche_elastique_maximale(l_portee), "mm", "dimension",
    ))
    r.verification = verifier_fleche_contre_la_limite(fleche, maximale, "5.4.2")
    return r
