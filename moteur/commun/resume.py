"""
Résumé des vérifications (issue #85 ; simplifié par datum-retours #22).

Une ligne par vérification : article, charge pondérée, résistance pondérée, ratio et statut, et la
vérification qui gouverne (ratio le plus élevé). Aucun nouveau calcul : les valeurs viennent telles
quelles des traces (Resultat). Le résumé sert à la page résumé de la note de calcul PDF et au tableau
« Résumé » de l'interface (mêmes lignes aux deux endroits).

Deux façons de faire le résumé :

- resume() : seulement les vérifications faites (charge pondérée entrée). Sert au résumé d'un projet
  (projet.resume_du_projet()), qui garde la vérification qui gouverne chaque élément.
- resume_des_verifications_offertes() (datum-retours #22) : **toutes** les vérifications offertes au
  compte, dans l'ordre des onglets, chacune avec son statut :
    - « Conforme » ou « Non conforme » : la vérification est faite (5.1.2) ;
    - « Charge manquante » : la résistance pondérée est calculée, mais la charge pondérée n'est pas
      entrée (la résistance est affichée, la charge et le ratio sont « — ») ;
    - « Non calculé » : aucune trace (données manquantes, ex. pas de longueur d'appui) ; charge,
      résistance et ratio « — ».
  Une vérification qui n'est pas offerte au compte n'est pas passée à la fonction : elle est absente
  du résumé (décision de l'utilisateur, datum-retours #22).

Le résumé reçoit déjà le nom de l'élément : les projets de plusieurs éléments (issue #85, étapes 2 et 3)
n'auront pas à le changer.
"""

from dataclasses import dataclass, replace

from moteur.commun.resultat import Resultat

# Statuts d'une ligne du résumé (datum-retours #22)
CONFORME = "Conforme"
NON_CONFORME = "Non conforme"
CHARGE_MANQUANTE = "Charge manquante"
NON_CALCULE = "Non calculé"

# Conversion de l'unité d'une étape de la trace (unités de base de la norme : N, N·mm) vers l'unité du
# résumé (celle de la vérification finale : kN, kN·m). Les fonctions de vérification divisent la
# résistance par ces mêmes nombres avant de la comparer à la charge (ex. 6.5.4 : v_r / 1000), donc une
# résistance « Charge manquante » est affichée exactement comme si la charge était entrée.
#   N / 1000 = kN ; N·mm / 1 000 000 = kN·m
DIVISEUR_DE_L_ETAPE_VERS_LE_RESUME = {
    ("N", "kN"): 1000,
    ("N·mm", "kN·m"): 1_000_000,
}


@dataclass(frozen=True)
class VerificationPrevue:
    """
    Une vérification qui peut paraître dans le résumé, même si elle n'est pas encore faite
    (datum-retours #22). Ce sont les symboles de la norme pour cette vérification : ils servent à
    afficher la ligne et à trouver la résistance pondérée dans la trace.

    Args:
        titre (str): Titre de la vérification (ex. « Compression perpendiculaire au fil »). N'est plus
            affiché dans le tableau (datum-retours #22), mais garde la ligne lisible dans le code et les
            tests.
        article (str): Article principal (ex. « 6.5.6.2 »), le même que celui de la trace.
        symbole_charge (str): Symbole de la charge pondérée en LaTeX (ex. « R_f »).
        symbole_resistance (str): Symbole de la résistance pondérée en LaTeX (ex. « Q_r ») : c'est aussi
            le symbole de l'étape de la trace qui la calcule.
        unite (str): Unité métrique du résumé (ex. « kN », « kN·m »), celle de la vérification finale.
        grandeur (str | None): Grandeur pour l'affichage en impérial (voir unites.GRANDEURS).
    """

    titre: str
    article: str
    symbole_charge: str
    symbole_resistance: str
    unite: str
    grandeur: str | None = None


@dataclass(frozen=True)
class LigneDuResume:
    """
    Une ligne du résumé : une vérification.

    Args:
        element (str): Nom de l'élément (ex. « Poutre P-1 : 2-2x10 »).
        titre (str): Titre de la vérification (ex. « Résistance au moment de flexion »).
        article (str): Article principal de la vérification (ex. « 6.5.3 »).
        symbole_charge (str): Symbole de la charge pondérée en LaTeX (ex. « M_f »).
        charge (float | None): Charge pondérée, en unités métriques. None : pas entrée.
        symbole_resistance (str): Symbole de la résistance pondérée en LaTeX (ex. « M_r »).
        resistance (float | None): Résistance pondérée, dans la même unité que la charge. None : pas
            calculée.
        unite (str): Unité métrique de la charge et de la résistance (ex. « kN·m »).
        grandeur (str | None): Grandeur pour l'affichage en impérial (voir unites.GRANDEURS).
        ratio (float | None): Ratio charge / résistance (infini si la résistance est nulle ou négative).
            None : vérification pas faite.
        respecte (bool | None): True si l'état limite est respecté. None : vérification pas faite.
        gouverne (bool): True pour la vérification qui gouverne (ratio le plus élevé).
        statut (str): CONFORME, NON_CONFORME, CHARGE_MANQUANTE ou NON_CALCULE.
    """

    element: str
    titre: str
    article: str
    symbole_charge: str
    charge: float | None
    symbole_resistance: str
    resistance: float | None
    unite: str
    grandeur: str | None
    ratio: float | None
    respecte: bool | None
    gouverne: bool
    statut: str


def _ligne_de_la_verification_faite(element: str, r: Resultat) -> LigneDuResume:
    """Ligne d'une trace qui a sa vérification finale : valeurs prises telles quelles de la trace."""
    v = r.verification
    return LigneDuResume(
        element=element,
        titre=r.titre,
        article=r.article,
        symbole_charge=v.symbole_charge,
        charge=v.charge,
        symbole_resistance=v.symbole_resistance,
        resistance=v.resistance,
        unite=v.unite,
        grandeur=v.grandeur,
        ratio=v.ratio,
        respecte=v.respecte,
        gouverne=False,  # marquée ensuite par _marquer_celle_qui_gouverne()
        statut=CONFORME if v.respecte else NON_CONFORME,
    )


def _marquer_celle_qui_gouverne(lignes: list[LigneDuResume]) -> list[LigneDuResume]:
    """
    Marque la vérification qui gouverne : le ratio le plus élevé parmi les vérifications faites ; à
    ratios égaux, la première. Une résistance nulle ou négative donne un ratio infini (Verification),
    qui gouverne donc toujours. Les lignes « Charge manquante » et « Non calculé » n'ont pas de ratio :
    elles ne gouvernent jamais. Sans vérification faite, aucune ligne ne gouverne.
    """
    faites = [i for i, l in enumerate(lignes) if l.ratio is not None]
    if not faites:
        return lignes
    indice_qui_gouverne = max(faites, key=lambda i: lignes[i].ratio)  # max() garde le premier à égalité
    return [replace(l, gouverne=i == indice_qui_gouverne) for i, l in enumerate(lignes)]


def resume(resultats: list[tuple]) -> list[LigneDuResume]:
    """
    Résumé des vérifications faites, dans l'ordre reçu (issue #85).

    Une trace sans vérification finale (charge pondérée pas encore entrée) n'a pas de ligne : c'est le
    résumé d'un projet (projet.resume_du_projet()). Pour le tableau de la page et la note, qui montrent
    toutes les vérifications offertes, voir resume_des_verifications_offertes().

    Args:
        resultats (list[tuple]): (nom de l'élément, trace), (nom de l'élément, trace, en test), etc.,
            comme pour la note de calcul (note_de_calcul.donnees_de_la_note()). Les éléments après la
            trace sont ignorés ici.

    Returns:
        list[LigneDuResume]: Une ligne par vérification faite ; liste vide s'il n'y en a aucune.
    """
    return _marquer_celle_qui_gouverne([
        _ligne_de_la_verification_faite(element, r)
        for element, r, *_ in resultats
        if r.verification is not None
    ])


def resume_des_verifications_offertes(
    verifications: list[tuple[str, VerificationPrevue, Resultat | None]],
) -> list[LigneDuResume]:
    """
    Résumé de toutes les vérifications offertes, faites ou non, dans l'ordre reçu (datum-retours #22).

    Statut de chaque ligne (voir aussi la docstring du module) :
        - trace avec sa vérification finale : « Conforme » ou « Non conforme » (5.1.2), valeurs de la
          trace ;
        - trace sans vérification finale (charge pondérée pas entrée) : « Charge manquante », avec la
          résistance pondérée de la trace (étape dont le symbole est symbole_resistance), convertie dans
          l'unité du résumé ; charge et ratio None ;
        - pas de trace (None), ou trace sans l'étape de la résistance : « Non calculé » ; charge,
          résistance et ratio None.

    Args:
        verifications (list[tuple[str, VerificationPrevue, Resultat | None]]): (nom de l'élément,
            vérification prévue, trace ou None si elle n'est pas calculée), dans l'ordre des onglets.
            Seulement les vérifications offertes au compte (les autres sont absentes du résumé).

    Returns:
        list[LigneDuResume]: Une ligne par vérification reçue ; « gouverne » marque la vérification faite
        au ratio le plus élevé (aucune s'il n'y a pas de vérification faite).

    Raises:
        ValueError: Si l'unité de l'étape de la résistance ne peut pas être convertie dans l'unité du
            résumé (voir DIVISEUR_DE_L_ETAPE_VERS_LE_RESUME) : mieux vaut une erreur qu'une valeur
            affichée dans la mauvaise unité.
    """
    lignes = []
    for element, prevue, r in verifications:
        if r is not None and r.verification is not None:
            lignes.append(_ligne_de_la_verification_faite(element, r))
            continue
        resistance = None
        if r is not None:
            try:
                etape = r.etape(prevue.symbole_resistance)
            except KeyError:
                etape = None  # trace sans résistance : traitée comme « Non calculé »
            if etape is not None:
                if etape.unite == prevue.unite:
                    diviseur = 1
                else:
                    try:
                        diviseur = DIVISEUR_DE_L_ETAPE_VERS_LE_RESUME[(etape.unite, prevue.unite)]
                    except KeyError:
                        raise ValueError(
                            f"Résumé : unité de {prevue.symbole_resistance} ({etape.unite}) impossible à "
                            f"convertir en {prevue.unite}."
                        ) from None
                resistance = etape.valeur / diviseur
        lignes.append(LigneDuResume(
            element=element,
            titre=r.titre if r is not None else prevue.titre,
            article=prevue.article,
            symbole_charge=prevue.symbole_charge,
            charge=None,  # charge pondérée pas entrée (ou vérification pas calculée)
            symbole_resistance=prevue.symbole_resistance,
            resistance=resistance,
            unite=prevue.unite,
            grandeur=prevue.grandeur,
            ratio=None,
            respecte=None,
            gouverne=False,
            statut=CHARGE_MANQUANTE if resistance is not None else NON_CALCULE,
        ))
    return _marquer_celle_qui_gouverne(lignes)
