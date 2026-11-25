"""
Projets : plusieurs éléments, enregistrés dans un fichier « .datum » (issue #85, étape 2).

Décisions de l'utilisateur (issue #85) :
- le projet est enregistré dans un fichier « .datum » (JSON) que l'utilisateur télécharge et rouvre ;
  rien n'est gardé sur un serveur ;
- **option A** : le fichier garde seulement les **données d'entrée** de chaque élément, jamais les
  résultats. À l'ouverture, l'application refait tous les calculs avec la version actuelle du moteur et
  l'édition de la norme notée dans le fichier (ARCHITECTURE.md, section 9). Un correctif de calcul
  profite donc aux projets rouverts, et un fichier modifié à la main ne peut pas contenir un faux
  résultat ;
- le résumé d'un projet a **une ligne par élément**, avec son ratio qui gouverne.

Aucune formule de la norme ici : ce module ne fait que lire, écrire et valider le fichier.
"""

import json
import math
from dataclasses import asdict, dataclass, field, fields

from moteur import VERSION
from moteur.commun import registre
from moteur.commun.note_de_calcul import EnTete
from moteur.commun.resultat import Resultat
from moteur.commun.resume import LigneDuResume, resume

FORMAT = 1  # numéro du format du fichier : augmenté à chaque changement incompatible
EXTENSION = ".datum"
TYPE_DE_FICHIER = "datum-projet"

Valeur = str | int | float | bool | None  # valeur d'une donnée d'entrée (JSON simple)


class FichierInvalide(ValueError):
    """Fichier « .datum » illisible, incomplet ou d'un format inconnu (message pour l'utilisateur)."""


@dataclass
class Element:
    """
    Un élément du projet (ex. « Poutre P-1 : 2-2x10 »).

    Args:
        nom (str): Nom de l'élément, affiché dans la note et le résumé.
        edition (str): Dossier de l'édition de la norme (ex. "csa_o86_19") avec laquelle les calculs
            sont refaits.
        entrees (dict[str, Valeur]): Données d'entrée, telles qu'entrées par l'utilisateur (matériau,
            dimensions, coefficients choisis, charges, appuis…), en unités métriques. Aucun résultat.
    """

    nom: str
    edition: str
    entrees: dict[str, Valeur] = field(default_factory=dict)


@dataclass
class Projet:
    """
    Un projet : l'en-tête de la note de calcul et la liste des éléments.

    Args:
        en_tete (EnTete): En-tête de la note (client, projet, adresse, dossier…).
        elements (list[Element]): Éléments, dans l'ordre choisi par l'utilisateur.
    """

    en_tete: EnTete = field(default_factory=EnTete)
    elements: list[Element] = field(default_factory=list)


# --- Écriture et lecture du fichier ---

def vers_json(projet: Projet) -> str:
    """
    Texte du fichier « .datum » d'un projet (JSON, UTF-8, indenté pour rester lisible).

    Raises:
        FichierInvalide: Si un élément est invalide (voir _valider_element()).
    """
    for element in projet.elements:
        _valider_element(element)
    contenu = {
        "type": TYPE_DE_FICHIER,
        "format": FORMAT,
        "version": VERSION,  # version de Datum qui a écrit le fichier (information seulement)
        "en_tete": asdict(projet.en_tete),
        "elements": [
            {"nom": e.nom, "edition": e.edition, "entrees": dict(e.entrees)} for e in projet.elements
        ],
    }
    return json.dumps(contenu, ensure_ascii=False, indent=2, allow_nan=False)


def depuis_json(texte: str | bytes) -> Projet:
    """
    Projet lu dans un fichier « .datum ».

    Le fichier est refusé au complet à la moindre erreur : aucun projet partiel n'est ouvert.

    Args:
        texte (str | bytes): Contenu du fichier.

    Raises:
        FichierInvalide: Si le fichier n'est pas un projet Datum valide, avec la raison.
    """
    try:
        contenu = json.loads(texte, parse_constant=_refuser_constante)
    except (ValueError, UnicodeDecodeError) as erreur:
        raise FichierInvalide("Le fichier n'est pas un projet Datum (JSON illisible).") from erreur

    if not isinstance(contenu, dict) or contenu.get("type") != TYPE_DE_FICHIER:
        raise FichierInvalide("Le fichier n'est pas un projet Datum.")
    version = contenu.get("format")
    if not isinstance(version, int) or isinstance(version, bool):
        raise FichierInvalide("Le fichier n'indique pas son format.")
    if version > FORMAT:
        raise FichierInvalide(
            f"Le fichier vient d'une version plus récente de Datum (format {version}) : mettez "
            "l'application à jour."
        )
    if version < 1:
        raise FichierInvalide(f"Format de fichier inconnu : {version}.")
    # Version de Datum qui a écrit le fichier : information seulement (les calculs sont toujours refaits
    # avec la version actuelle, option A). Facultative : absente des fichiers écrits avant la 0.1.0.
    if not isinstance(contenu.get("version", ""), str):
        raise FichierInvalide("Version de Datum invalide dans le fichier.")

    en_tete = contenu.get("en_tete", {})
    champs = {f.name for f in fields(EnTete)}
    if not isinstance(en_tete, dict) or not set(en_tete) <= champs:
        raise FichierInvalide("En-tête du projet invalide.")
    if not all(isinstance(v, str) for v in en_tete.values()):
        raise FichierInvalide("En-tête du projet invalide : chaque champ doit être un texte.")

    elements = contenu.get("elements", [])
    if not isinstance(elements, list):
        raise FichierInvalide("Liste des éléments invalide.")
    projet = Projet(en_tete=EnTete(**en_tete))
    for i, e in enumerate(elements, start=1):
        if not isinstance(e, dict) or not {"nom", "edition", "entrees"} <= set(e):
            raise FichierInvalide(f"Élément {i} incomplet (nom, édition et entrées requis).")
        element = Element(nom=e["nom"], edition=e["edition"], entrees=e["entrees"])
        _valider_element(element, i)
        projet.elements.append(element)
    return projet


def _refuser_constante(constante: str):
    """NaN et Infinity ne sont pas des données d'entrée valides."""
    raise ValueError(f"Valeur {constante} refusée.")


def _valider_element(element: Element, numero: int | None = None) -> None:
    """
    Vérifie un élément : nom non vide, édition connue et entrées simples (texte, nombre fini, booléen
    ou vide). Les listes et les objets imbriqués sont refusés pour garder le fichier simple.

    Raises:
        FichierInvalide: Avec la raison.
    """
    quel = f"Élément {numero}" if numero is not None else "Élément"
    if not isinstance(element.nom, str) or not element.nom.strip():
        raise FichierInvalide(f"{quel} : nom manquant.")
    quel = f"{quel} « {element.nom} »"
    try:
        if not isinstance(element.edition, str):
            raise KeyError(element.edition)
        registre.nom_de_l_edition(element.edition)
    except KeyError as erreur:
        raise FichierInvalide(f"{quel} : édition de norme inconnue ({element.edition!r}).") from erreur
    if not isinstance(element.entrees, dict):
        raise FichierInvalide(f"{quel} : entrées invalides.")
    for cle, valeur in element.entrees.items():
        if not isinstance(cle, str) or not cle:
            raise FichierInvalide(f"{quel} : nom d'entrée invalide.")
        if valeur is not None and not isinstance(valeur, (str, int, float, bool)):
            raise FichierInvalide(f"{quel} : entrée {cle!r} invalide (texte, nombre ou oui/non attendu).")
        if isinstance(valeur, float) and not math.isfinite(valeur):
            raise FichierInvalide(f"{quel} : entrée {cle!r} invalide (nombre infini).")


# --- Résumé du projet ---

def resume_du_projet(elements: list[tuple[str, list[Resultat]]]) -> list[LigneDuResume]:
    """
    Résumé d'un projet : une ligne par élément, avec la vérification qui gouverne cet élément (ratio
    le plus élevé ; décision de l'utilisateur, issue #85). Réutilise resume() : aucun nouveau calcul.

    Les traces sont celles **recalculées** à l'ouverture du projet (option A), jamais lues du fichier.
    Un élément sans vérification faite n'a pas de ligne. Dans le résultat, « gouverne » marque l'élément
    dont le ratio est le plus élevé du projet ; à ratios égaux, le premier.

    Args:
        elements (list[tuple[str, list[Resultat]]]): (nom de l'élément, traces de ses vérifications).

    Returns:
        list[LigneDuResume]: Une ligne par élément vérifié, dans l'ordre reçu.
    """
    lignes = []
    for nom, resultats in elements:
        qui_gouverne = [l for l in resume([(nom, r) for r in resultats]) if l.gouverne]
        lignes += qui_gouverne  # au plus une ligne : resume() marque une seule vérification
    if not lignes:
        return []
    ratios = [l.ratio for l in lignes]
    indice = ratios.index(max(ratios))
    return [_avec_gouverne(l, i == indice) for i, l in enumerate(lignes)]


def _avec_gouverne(ligne: LigneDuResume, gouverne: bool) -> LigneDuResume:
    return LigneDuResume(**{**asdict(ligne), "gouverne": gouverne})
