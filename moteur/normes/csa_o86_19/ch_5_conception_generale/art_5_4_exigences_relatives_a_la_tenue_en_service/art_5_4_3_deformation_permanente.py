"""
CSA O86:19 - 5.4.3 Déformation permanente (p. 44).

« Les éléments de charpente qui supportent des charges de durée d'application continue doivent être
conçus de manière à limiter les déformations permanentes. Faute d'une méthode d'évaluation plus précise
des limites acceptables pour les flèches, une flèche égale au 1/360 de la portée doit être considérée
comme étant la limite supérieure à ne pas dépasser dans le calcul de la flèche élastique due aux
combinaisons de charges de durée d'application continue. »
(« [...] an upper limit of 1/360 of the span shall be imposed on the elastic deflection due to long-term
service load combinations. »)

La portée ℓ (3.2, p. 37) est écrite `l_portee` dans le code (voir art_5_4_2_fleche_elastique.py).
"""

from moteur.commun.registre import enregistrer
from moteur.commun.resultat import Donnee, Etape, Resultat
from moteur.normes.csa_o86_19 import NORME
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_4_exigences_relatives_a_la_tenue_en_service.art_5_4_2_fleche_elastique import (  # noqa: E501
    verifier_fleche_contre_la_limite,
)

EDITION = "csa_o86_19"
FRACTION_DE_LA_PORTEE = 360  # 5.4.3 : flèche (charges continues) <= 1/360 de la portée


def fleche_elastique_maximale_charges_continues(l_portee: float) -> float:
    """
    5.4.3 Flèche élastique maximale sous les combinaisons de charges de durée d'application continue :
    ℓ / 360 (faute d'une méthode d'évaluation plus précise).

    Args:
        l_portee (float): ℓ, portée, mm (3.2).

    Returns:
        float: Flèche élastique maximale, mm.

    Raises:
        ValueError: Si la portée n'est pas positive.
    """
    if l_portee <= 0:
        raise ValueError("La portée ℓ doit être positive (5.4.3).")
    return l_portee / FRACTION_DE_LA_PORTEE


@enregistrer(EDITION, "5.4.3", "Déformation permanente")
def verifier_deformation_permanente(l_portee: float, fleche: float) -> Resultat:
    """
    5.4.3 Déformation permanente : flèche élastique sous les combinaisons de charges de durée
    d'application continue <= ℓ / 360 (faute d'une méthode d'évaluation plus précise).

    La flèche vient de l'analyse de l'ingénieur (réponse de l'utilisateur, 28 novembre 2026, PR #119).

    Args:
        l_portee (float): ℓ, portée, mm (3.2). Affichage : ℓ.
        fleche (float): Flèche élastique sous les charges de durée d'application continue, mm.

    Returns:
        Resultat: Trace : ℓ / 360, puis la flèche comparée à cette limite (en mm).

    Raises:
        ValueError: Si la portée n'est pas positive ou si la flèche est négative.
    """
    r = Resultat(NORME, "5.4.3", "Déformation permanente")
    r.ajouter_donnee(Donnee(r"\ell", "Portée", l_portee, "mm", "longueur"))
    r.ajouter_donnee(Donnee("", "Flèche élastique (charges de durée d'application continue)", fleche,
                            "mm", "dimension"))  # pas de symbole à 5.4.3
    maximale = r.ajouter_etape(Etape(
        "5.4.3", "Flèche élastique maximale (charges continues)", "", r"\ell / 360", rf"{l_portee:g} / 360",
        fleche_elastique_maximale_charges_continues(l_portee), "mm", "dimension",
    ))
    r.verification = verifier_fleche_contre_la_limite(fleche, maximale, "5.4.3")
    return r
