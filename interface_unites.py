"""
Unités dans l'interface Streamlit : saisie libre et affichage dans les deux unités (retour
LeRepere-GP/datum-retours#10, PR #99).

Tous les calculs se font en métrique (CLAUDE.md, ARCHITECTURE.md section 8). Ce module sert UNIQUEMENT à
l'affichage : il lit les champs et rend toujours au moteur des valeurs métriques (mm, kN, kN·m), avec la
fonction générale moteur/commun/unites.lire_grandeur() ; aucune formule de la norme ici.

Décisions de l'utilisateur (PR #99) :
- chaque champ accepte n'importe quelle unité, même mélangées, et fonctionne comme une calculatrice :
  « 8 pi 38 mm » = 2476.4 mm, « 3 1/2 po », « 5 kN », « 1124 lb », « (2+3)/2 po », « 8 pieds + 36 po - 50 mm » ;
  « - » est toujours une soustraction ;
- un nombre sans unité prend l'unité par défaut, choisie dans la barre latérale (deux bascules
  indépendantes : dimensions, en impérial au départ, et charges, en métrique au départ) ;
- avec « + », un nombre sans unité prend l'unité du terme suivant : « 2 + 3 po » = 5 po ;
- le champ garde le texte entré ; une ligne dessous donne la valeur retenue dans les deux unités ;
- les résultats sont affichés dans les deux unités (ex. « 14.34 kN (3224 lb) »).

Un texte déjà entré garde son sens si l'unité par défaut change (« 89 » entré en mm reste 89 mm).
Les dimensions nominales (ex. « 2x6 ») et les dimensions brutes restent en po (retour #10).
"""

import streamlit as st

from moteur.commun.nombres import cs
from moteur.commun.unites import (
    ecrire_pieds_pouces,
    ecrire_pouces,
    grandeur,
    lire_grandeur,
    vers_imperial,
)

METRIQUE = "Métrique"
IMPERIAL = "Impérial"
SYSTEMES = (METRIQUE, IMPERIAL)

# Bascule de l'unité par défaut de chaque grandeur (clé de st.session_state)
DIMENSIONS = "unites_dimensions"
CHARGES = "unites_charges"
# Unité par défaut au départ (décision de l'utilisateur, PR #99) : dimensions en impérial, charges en
# métrique
_DEPART = {DIMENSIONS: IMPERIAL, CHARGES: METRIQUE}
_BASCULE = {
    "dimension": DIMENSIONS,
    "longueur": DIMENSIONS,
    "aire": DIMENSIONS,
    "force": CHARGES,
    "moment": CHARGES,
    "contrainte": CHARGES,
    "pression": CHARGES,  # charges du K_D (5.3.2.2) : unité seulement, aucune conversion
}

# Exemples de saisie, dans l'aide de chaque champ
_EXEMPLES = {
    "dimension": "Toute unité : ex. 89 mm, 3 1/2 po, 3 1/2\", 1' 2 1/4\", 8 pi 38 mm.",
    "longueur": "Toute unité : ex. 3000 mm, 3 m, 8' 6\", 8 pi 6 po, 3 pi 2 1/4 po, 8 pi 38 mm.",
    "force": "Toute unité : ex. 5 kN, 5000 N, 1124 lb, 1.2 kip.",
    "moment": "Toute unité : ex. 4.5 kN·m, 4500 N·m, 40 000 lb·po, 3300 lb·pi.",
}
_CALCULATRICE = (
    "Calculs permis : + - * / ^ %, parenthèses (ex. (2 + 3)/2 po, 8 pi + 36 po - 50 mm). "
    "« - » est toujours une soustraction : écrire 8' 6\" ou 2 1/4 po, sans tiret. Décimales avec un point "
    "ou une virgule (3.5 ou 3,5) ; milliers avec une espace (40 000)."
)


def choisir_systemes() -> None:
    """
    Bascules de l'unité par défaut (nombres entrés sans unité) dans la barre latérale : une pour les
    dimensions (impérial au départ), une pour les charges (métrique au départ) ; gardées pour la séance.
    """
    aide = """Unité d'un nombre entré sans unité. On peut toujours écrire l'unité dans le champ
    (ex. 89 mm, 3 1/2 po, 5 kN, 1124 lb), même mélangées (8 pi 38 mm), avec des opérations
    ((2 + 3)/2 po). Les calculs se font en
    métrique ; les résultats sont affichés dans les deux unités."""
    st.sidebar.markdown("**Unité par défaut**")
    st.sidebar.segmented_control(
        "Dimensions", options=SYSTEMES, default=_DEPART[DIMENSIONS], key=DIMENSIONS, width="stretch",
        help="Métrique : mm. Impérial : po (dimensions) et pi (longueurs). " + aide,
    )
    st.sidebar.segmented_control(
        "Charges", options=SYSTEMES, default=_DEPART[CHARGES], key=CHARGES, width="stretch",
        help="Métrique : kN, kN·m. Impérial : lb, lb·po. " + aide,
    )


def en_imperial(nom_grandeur: str) -> bool:
    """True si l'unité par défaut de la grandeur est impériale (valeur de départ si rien n'est choisi)."""
    cle = _BASCULE[nom_grandeur]
    return (st.session_state.get(cle) or _DEPART[cle]) == IMPERIAL


def unite(nom_grandeur: str) -> str:
    """Unité par défaut de la grandeur (ex. « mm », « po » ; « pi » pour une longueur en impérial)."""
    if nom_grandeur == "pression":
        return "lb/pi²" if en_imperial(nom_grandeur) else "kPa"
    g = grandeur(nom_grandeur)
    return g.unite_imperiale if en_imperial(nom_grandeur) else g.unite_metrique


# --- Textes des résultats : les deux unités ---

_ESPACE_INSECABLE = "\u00a0"  # entre les milliers et entre le nombre et son unité : pas de coupure


def nombre(valeur: float, decimales: int) -> str:
    """
    Nombre avec un point décimal et une espace insécable entre les milliers (ex. 150000 -> « 150 000 » ;
    2476.4 -> « 2 476.4 »), comme dans les commentaires du code (CLAUDE.md).
    """
    return f"{valeur:,.{decimales}f}".replace(",", _ESPACE_INSECABLE)


def _avec_milliers(texte_nombre: str) -> str:
    """« 150000 » -> « 150 000 » ; « 2476.4 » -> « 2 476.4 » ; garde le nombre de décimales du texte."""
    entier, _, decimales = texte_nombre.partition(".")
    signe = "-" if entier.startswith("-") else ""
    entier = f"{int(entier.lstrip('-')):,}".replace(",", _ESPACE_INSECABLE)
    return signe + entier + (f".{decimales}" if decimales else "")

def _metrique(valeur: float, nom_grandeur: str, decimales: int | None) -> str:
    g = grandeur(nom_grandeur)
    if decimales is None and nom_grandeur in ("dimension", "longueur"):
        # mm : au dixième, sans zéro inutile (ex. « 89 mm », « 88.9 mm », « 2476.4 mm »)
        texte_nombre = _avec_milliers(f"{valeur:.1f}".rstrip("0").rstrip("."))
    else:
        texte_nombre = nombre(valeur, g.decimales_metrique if decimales is None else decimales)
    return f"{texte_nombre} {g.unite_metrique}"


def _imperial(valeur: float, nom_grandeur: str) -> str:
    if nom_grandeur == "longueur":
        return ecrire_pieds_pouces(valeur)
    if nom_grandeur == "dimension":
        return f"{ecrire_pouces(valeur)} po"  # au 1/16 po près
    g = grandeur(nom_grandeur)
    return f"{nombre(vers_imperial(valeur, nom_grandeur), g.decimales_imperiale)} {g.unite_imperiale}"


def texte(valeur_metrique: float, nom_grandeur: str, decimales: int | None = None) -> str:
    """
    Valeur métrique affichée dans les deux unités, avec un point décimal (décision de l'utilisateur).

    Exemples : texte(38, "dimension") -> « 38 mm (1-1/2 po) » ;
    texte(2590.8, "longueur") -> « 2590.8 mm (8 pi - 6 po) » ; texte(14.34, "force") -> « 14.34 kN (3224 lb) ».

    Args:
        valeur_metrique (float): Valeur en unité métrique de la grandeur (mm, kN, kN·m, MPa...).
        nom_grandeur (str): Grandeur de moteur/commun/unites.py.
        decimales (int | None, optional): Décimales imposées en métrique. Default to celles de la grandeur.
    """
    return f"{_metrique(valeur_metrique, nom_grandeur, decimales)} ({_imperial(valeur_metrique, nom_grandeur)})"


def texte_significatif(valeur_metrique: float, nom_grandeur: str) -> str:
    """
    Comme texte(), avec le même nombre de chiffres significatifs que la note de calcul
    (moteur/commun/nombres.py ; ex. « 14.7 kN (3220 lb) »). Sert au tableau « Résumé ».
    """
    g = grandeur(nom_grandeur)
    return (
        f"{_avec_milliers(cs(valeur_metrique))} {g.unite_metrique} "
        f"({_avec_milliers(cs(vers_imperial(valeur_metrique, nom_grandeur)))} {g.unite_imperiale})"
    )


def latex(valeur_metrique: float, nom_grandeur: str, decimales: int | None = None) -> str:
    """
    Comme texte(), pour une formule LaTeX : dans \\text{...}, qui garde les espaces et les unités droites
    (ex. « \\text{22.51 kN (5 060 lb)} » ; sans lui, KaTeX affiche « 22.51kN(5060lb) »).
    """
    return "\\text{" + texte(valeur_metrique, nom_grandeur, decimales) + "}"


# --- Champs ---

def _cle_metrique(key: str) -> str:
    return f"_{key}__metrique"  # valeur métrique retenue, gardée pour la séance


def _cle_texte_lu(key: str) -> str:
    return f"_{key}__texte_lu"  # texte qui a donné la valeur retenue


def champ(
    libelle: str,
    nom_grandeur: str,
    key: str,
    conteneur=st,
    min_value: float | None = None,
    max_value: float | None = None,
    **kwargs,
) -> float | None:
    """
    Champ texte en saisie libre (n'importe quelle unité, même mélangées), qui rend une valeur métrique
    (mm, kN, kN·m), ou None s'il est vide, illisible ou hors des bornes (avec un message).

    Le champ garde le texte entré ; une ligne dessous donne la valeur retenue dans les deux unités. Un
    nombre sans unité prend l'unité par défaut (barre latérale). Le texte n'est relu que s'il change :
    changer l'unité par défaut ne change pas le sens d'une valeur déjà entrée.

    Args:
        libelle (str): Libellé ; « {unite} » y est remplacé par l'unité par défaut (ex. « $L_b$ ({unite}) »).
        nom_grandeur (str): « dimension », « longueur », « force » ou « moment ».
        key (str): Clé du champ.
        conteneur (optional): Où placer le champ (st, une colonne...). Default to st.
        min_value, max_value (float | None, optional): Bornes, en métrique. Default to None.
        **kwargs: Autres arguments de st.text_input (placeholder, help, icon, width...).

    Returns:
        float | None: Valeur en métrique (mm, kN, kN·m), ou None.
    """
    cle_metrique, cle_texte_lu = _cle_metrique(key), _cle_texte_lu(key)
    if key not in st.session_state:
        st.session_state[key] = st.session_state.get(cle_texte_lu) or ""
    aide = kwargs.pop("help", None)
    exemples = f"{_EXEMPLES[nom_grandeur]} {_CALCULATRICE} Sans unité : {unite(nom_grandeur)}."
    for inutile in ("step", "format", "value"):
        kwargs.pop(inutile, None)
    saisie = conteneur.text_input(
        libelle.replace("{unite}", unite(nom_grandeur).replace("·", " \\cdot ")),
        key=key,
        help=f"{aide} {exemples}" if aide else exemples,
        **kwargs,
    )

    if not saisie.strip():
        st.session_state[cle_metrique], st.session_state[cle_texte_lu] = None, ""
        return None
    if saisie != st.session_state.get(cle_texte_lu) or st.session_state.get(cle_metrique) is None:
        try:
            st.session_state[cle_metrique] = lire_grandeur(saisie, nom_grandeur, en_imperial(nom_grandeur))
        except ValueError:
            st.session_state[cle_metrique], st.session_state[cle_texte_lu] = None, ""
            conteneur.error(f"Valeur illisible : « {saisie} ». {exemples}", icon=":material/error:")
            return None
        st.session_state[cle_texte_lu] = saisie
    valeur = st.session_state[cle_metrique]

    if min_value is not None and valeur < min_value:
        conteneur.error(
            f"La valeur doit être d'au moins {texte(min_value, nom_grandeur)}.", icon=":material/error:"
        )
        return None
    if max_value is not None and valeur > max_value:
        conteneur.error(
            f"La valeur ne doit pas dépasser {_metrique(max_value, nom_grandeur, None)} "
            f"({vers_imperial(max_value, nom_grandeur):.3f} {grandeur(nom_grandeur).unite_imperiale}).",
            icon=":material/error:",
        )
        return None
    conteneur.caption(f"= {texte(valeur, nom_grandeur)}")
    return valeur


def remplir(key: str, valeur_metrique: float | None) -> None:
    """
    Remplit un champ créé par champ() (ex. largeur d'appui préremplie avec la largeur de l'élément),
    avec sa valeur en mm. À appeler avant d'afficher le champ.
    """
    texte_ = "" if valeur_metrique is None else f"{valeur_metrique:g} mm"
    st.session_state[key] = texte_
    st.session_state[_cle_texte_lu(key)] = texte_
    st.session_state[_cle_metrique(key)] = valeur_metrique
