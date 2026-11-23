"""
Résumé des vérifications (issue #85, étape 1).

Une ligne par vérification faite : titre, article, charge pondérée, résistance pondérée, ratio et
statut, et la vérification qui gouverne (ratio le plus élevé). Aucun nouveau calcul : les valeurs
viennent telles quelles des traces (Resultat). Le résumé sert à la page résumé de la note de calcul PDF
et au tableau « Résumé » de l'interface.

Le résumé reçoit déjà une liste de (nom de l'élément, trace) : les projets de plusieurs éléments
(issue #85, étapes 2 et 3) n'auront pas à le changer.
"""

from dataclasses import dataclass

from moteur.commun.resultat import Resultat


@dataclass(frozen=True)
class LigneDuResume:
    """
    Une ligne du résumé : une vérification faite.

    Args:
        element (str): Nom de l'élément (ex. « Poutre P-1 : 2-2x10 »).
        titre (str): Titre de la vérification (ex. « Résistance au moment de flexion »).
        article (str): Article principal de la vérification (ex. « 6.5.3 »).
        symbole_charge (str): Symbole de la charge pondérée en LaTeX (ex. « M_f »).
        charge (float): Charge pondérée, en unités métriques.
        symbole_resistance (str): Symbole de la résistance pondérée en LaTeX (ex. « M_r »).
        resistance (float): Résistance pondérée, dans la même unité que la charge.
        unite (str): Unité métrique de la charge et de la résistance (ex. « kN·m »).
        grandeur (str | None): Grandeur pour l'affichage en impérial (voir unites.GRANDEURS).
        ratio (float): Ratio charge / résistance (infini si la résistance est nulle ou négative).
        respecte (bool): True si l'état limite est respecté.
        gouverne (bool): True pour la vérification qui gouverne (ratio le plus élevé).
    """

    element: str
    titre: str
    article: str
    symbole_charge: str
    charge: float
    symbole_resistance: str
    resistance: float
    unite: str
    grandeur: str | None
    ratio: float
    respecte: bool
    gouverne: bool


def resume(resultats: list[tuple]) -> list[LigneDuResume]:
    """
    Résumé des vérifications faites, dans l'ordre reçu (issue #85).

    Une trace sans vérification finale (charge pondérée pas encore entrée) n'a pas de ligne. La
    vérification qui gouverne est celle du ratio le plus élevé ; à ratios égaux, la première. Une
    résistance nulle ou négative donne un ratio infini (Verification), qui gouverne donc toujours.

    Args:
        resultats (list[tuple]): (nom de l'élément, trace) ou (nom de l'élément, trace, en test), comme
            pour la note de calcul (note_de_calcul.donnees_de_la_note()). « en test » est ignoré ici.

    Returns:
        list[LigneDuResume]: Une ligne par vérification faite ; liste vide s'il n'y en a aucune.
    """
    faites: list[tuple[str, Resultat]] = [
        (element, r) for element, r, *_ in resultats if r.verification is not None
    ]
    if not faites:
        return []
    ratios = [r.verification.ratio for _, r in faites]
    indice_qui_gouverne = ratios.index(max(ratios))
    return [
        LigneDuResume(
            element=element,
            titre=r.titre,
            article=r.article,
            symbole_charge=r.verification.symbole_charge,
            charge=r.verification.charge,
            symbole_resistance=r.verification.symbole_resistance,
            resistance=r.verification.resistance,
            unite=r.verification.unite,
            grandeur=r.verification.grandeur,
            ratio=r.verification.ratio,
            respecte=r.verification.respecte,
            gouverne=i == indice_qui_gouverne,
        )
        for i, (element, r) in enumerate(faites)
    ]
