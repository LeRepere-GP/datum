"""
Bascules métrique / impérial de l'interface Streamlit (retour LeRepere-GP/datum-retours#10).

Tous les calculs se font en métrique (CLAUDE.md, ARCHITECTURE.md section 8). Ce module sert UNIQUEMENT à
l'affichage : il présente chaque champ et chaque résultat dans le système choisi dans la barre latérale,
et rend toujours au moteur des valeurs métriques (mm, kN, kN·m). Les conversions viennent de
moteur/commun/unites.py ; aucune formule de la norme ici.

Deux bascules indépendantes (demande de l'utilisateur, PR #99) :
- « Dimensions » : dimensions (mm / po), longueurs (mm / pi-po) et aires ;
- « Charges » : forces (kN / lb), moments (kN·m / lb·po) et contraintes (MPa / psi).

On peut basculer en tout temps : les valeurs entrées sont gardées (en métrique, exactes) et réaffichées
dans l'autre système. En impérial, les dimensions et les longueurs s'entrent en pieds, pouces et fractions
de pouce (ex. « 3-1/2 » po, « 8-6 » = 8 pi 6 po, « 3 pi 2-1/4 po »), avec la fonction générale
moteur/commun/unites.lire_imperial().

Les dimensions nominales (ex. « 2x6 ») et les dimensions brutes restent en po dans les deux systèmes
(décision de l'utilisateur, retour #10).
"""

import math

import streamlit as st

from moteur.commun.nombres import cs
from moteur.commun.unites import (
    ecrire_pieds_pouces,
    ecrire_pouces,
    grandeur,
    lire_imperial,
    vers_imperial,
    vers_metrique,
)

METRIQUE = "Métrique"
IMPERIAL = "Impérial"
SYSTEMES = (METRIQUE, IMPERIAL)

# Bascule de chaque grandeur (clé de st.session_state)
DIMENSIONS = "unites_dimensions"
CHARGES = "unites_charges"
_BASCULE = {
    "dimension": DIMENSIONS,
    "longueur": DIMENSIONS,
    "aire": DIMENSIONS,
    "force": CHARGES,
    "moment": CHARGES,
    "contrainte": CHARGES,
    "pression": CHARGES,  # charges du K_D (5.3.2.2) : unité seulement, aucune conversion
}

# Format et pas des champs numériques, par grandeur et par système (unités de moteur/commun/unites.py).
# En impérial, les dimensions (po) et les longueurs (pi-po) s'entrent dans un champ texte, en pieds,
# pouces et fractions de pouce (voir _champ_imperial() et unites.lire_imperial()).
_FORMAT_ET_PAS = {
    ("dimension", METRIQUE): ("%.0f", 1.0),  # mm
    ("longueur", METRIQUE): ("%.0f", 100.0),  # mm
    ("force", METRIQUE): ("%.2f", 1.0),  # kN
    ("force", IMPERIAL): ("%.0f", 100.0),  # lb
    ("moment", METRIQUE): ("%.2f", 1.0),  # kN·m
    ("moment", IMPERIAL): ("%.0f", 1000.0),  # lb·po
}

_PI_PO = "pi-po"  # unité affichée des longueurs en impérial


def choisir_systemes() -> None:
    """
    Bascules « Dimensions » et « Charges » dans la barre latérale, gardées pour la séance.
    Métrique par défaut.
    """
    aide = """Unités des entrées et des résultats affichés. On peut changer en tout temps : les valeurs
    entrées sont gardées. Les calculs se font toujours en métrique, comme dans la norme ; la note de
    calcul donne les deux unités."""
    st.sidebar.segmented_control(
        "Dimensions", options=SYSTEMES, default=METRIQUE, key=DIMENSIONS, width="stretch",
        help="Dimensions (mm / po) et longueurs (mm / pi-po). " + aide,
    )
    st.sidebar.segmented_control(
        "Charges", options=SYSTEMES, default=METRIQUE, key=CHARGES, width="stretch",
        help="Charges, résistances et moments (kN / lb, kN·m / lb·po) et contraintes (MPa / psi). " + aide,
    )


def systeme(nom_grandeur: str) -> str:
    """Système choisi pour la grandeur (METRIQUE si rien n'est choisi)."""
    return IMPERIAL if st.session_state.get(_BASCULE[nom_grandeur]) == IMPERIAL else METRIQUE


def en_imperial(nom_grandeur: str) -> bool:
    """True si la grandeur est affichée en impérial."""
    return systeme(nom_grandeur) == IMPERIAL


def unite(nom_grandeur: str) -> str:
    """Unité d'affichage de la grandeur dans le système choisi (ex. « mm » ou « po »)."""
    if nom_grandeur == "pression":
        return "lb/pi²" if en_imperial(nom_grandeur) else "kPa"
    g = grandeur(nom_grandeur)
    return g.unite_imperiale if en_imperial(nom_grandeur) else g.unite_metrique


def vers_affichage(valeur_metrique: float, nom_grandeur: str) -> float:
    """Valeur métrique (unités de moteur/commun/unites.py) dans le système choisi."""
    if en_imperial(nom_grandeur):
        return vers_imperial(valeur_metrique, nom_grandeur)
    return valeur_metrique


def depuis_affichage(valeur: float, nom_grandeur: str) -> float:
    """Valeur du système choisi, ramenée en métrique pour le moteur."""
    return vers_metrique(valeur, nom_grandeur) if en_imperial(nom_grandeur) else valeur


# --- Textes des résultats ---

def texte(valeur_metrique: float, nom_grandeur: str, decimales: int | None = None) -> str:
    """
    Valeur métrique affichée dans le système choisi, avec son unité et un point décimal.

    Exemples : texte(38, "dimension") -> « 38 mm » ou « 1.50 po » ;
    texte(14.75, "force") -> « 14.75 kN » ou « 3316 lb ».

    Args:
        valeur_metrique (float): Valeur en unité métrique de la grandeur (mm, kN, kN·m, MPa...).
        nom_grandeur (str): Grandeur de moteur/commun/unites.py.
        decimales (int | None, optional): Décimales imposées. Default to celles de la grandeur.
    """
    if nom_grandeur == "longueur" and en_imperial(nom_grandeur):
        return ecrire_pieds_pouces(valeur_metrique)
    g = grandeur(nom_grandeur)
    if decimales is None:
        decimales = g.decimales_imperiale if en_imperial(nom_grandeur) else g.decimales_metrique
    return f"{vers_affichage(valeur_metrique, nom_grandeur):.{decimales}f} {unite(nom_grandeur)}"


def texte_significatif(valeur_metrique: float, nom_grandeur: str) -> str:
    """
    Comme texte(), avec le même nombre de chiffres significatifs que la note de calcul
    (moteur/commun/nombres.py ; ex. « 14.7 kN » ou « 3320 lb »). Sert au tableau « Résumé ».
    """
    return f"{cs(vers_affichage(valeur_metrique, nom_grandeur))} {unite(nom_grandeur)}"


def latex(valeur_metrique: float, nom_grandeur: str, decimales: int | None = None) -> str:
    """Comme texte(), pour une formule LaTeX (« · » devient « \\cdot »)."""
    return texte(valeur_metrique, nom_grandeur, decimales).replace("·", " \\cdot ")


# --- Champs ---

def _cles(key: str, imperial: bool) -> tuple[str, str, str, str]:
    """Clés du champ affiché, du champ de l'autre système, de la valeur métrique et de la valeur initiale."""
    return (
        f"{key}__imperial" if imperial else key,
        key if imperial else f"{key}__imperial",
        f"_{key}__metrique",  # valeur métrique gardée pour la séance
        f"_{key}__initiale",  # valeur affichée à la bascule (pour éviter la dérive d'arrondi)
    )


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
    Champ dans le système choisi, qui rend une valeur métrique (ou None s'il est vide).

    La valeur entrée est gardée en métrique pour la séance : à la bascule, le champ affiche la même
    valeur dans l'autre système, aussi souvent qu'on veut. Une valeur non modifiée après la bascule garde
    sa valeur métrique exacte (pas d'erreur d'arrondi : 89 mm -> 3.50 po -> 89 mm).

    En métrique, la clé du champ est `key` (tests et code existants) ; en impérial, `key + "__imperial"`.
    En impérial, les dimensions et les longueurs s'entrent dans un champ texte en pieds, pouces et
    fractions de pouce (ex. « 3-1/2 », « 8-6 »).

    Args:
        libelle (str): Libellé ; « {unite} » y est remplacé par l'unité (ex. « $L_b$ ({unite}) »).
        nom_grandeur (str): Grandeur de moteur/commun/unites.py (dimension, longueur, force, moment).
        key (str): Clé de la valeur.
        conteneur (optional): Où placer le champ (st, une colonne...). Default to st.
        min_value, max_value (float | None, optional): Bornes, en métrique. Default to None.
        **kwargs: Autres arguments de st.number_input (placeholder, help, icon, width...).

    Returns:
        float | None: Valeur en métrique (mm, kN, kN·m), ou None.
    """
    imperial = en_imperial(nom_grandeur)
    if imperial and nom_grandeur in ("dimension", "longueur"):
        return _champ_imperial(libelle, nom_grandeur, key, conteneur, min_value, max_value, **kwargs)
    cle_du_champ, cle_de_l_autre, cle_metrique, cle_initiale = _cles(key, imperial)
    format_, pas = _FORMAT_ET_PAS[(nom_grandeur, systeme(nom_grandeur))]

    def affichee(valeur_metrique):
        if valeur_metrique is None:
            return None
        return float(format_ % vers_affichage(valeur_metrique, nom_grandeur))

    # Bornes arrondies vers l'intérieur : la borne affichée ne dépasse jamais la borne métrique
    # (ex. d_n <= 0.25 d, 6.5.4.4.2)
    facteur = 10 ** int(format_[2:-1])
    borne_min = None if min_value is None else (
        math.ceil(vers_affichage(min_value, nom_grandeur) * facteur - 1e-9) / facteur)
    borne_max = None if max_value is None else (
        math.floor(vers_affichage(max_value, nom_grandeur) * facteur + 1e-9) / facteur)

    # L'autre système est oublié : son champ sera rempli de nouveau à partir de la valeur métrique
    st.session_state.pop(cle_de_l_autre, None)
    if cle_du_champ not in st.session_state:
        st.session_state[cle_du_champ] = affichee(st.session_state.get(cle_metrique))
        st.session_state[cle_initiale] = st.session_state[cle_du_champ]
    # Une valeur hors des bornes (arrondi à la bascule, ou borne qui change avec l'élément) est ramenée
    # à la borne : Streamlit refuse une valeur hors des bornes
    actuelle = st.session_state[cle_du_champ]
    if actuelle is not None:
        bornee = actuelle
        if borne_min is not None:
            bornee = max(bornee, borne_min)
        if borne_max is not None:
            bornee = min(bornee, borne_max)
        if bornee != actuelle:
            st.session_state[cle_du_champ] = bornee
            metrique = st.session_state.get(cle_metrique)
            dans_les_bornes = metrique is not None and (
                (min_value is None or metrique >= min_value)
                and (max_value is None or metrique <= max_value)
            )
            # La valeur métrique respecte déjà les bornes (seul l'affichage est arrondi) : on la garde
            # exacte (ex. d_n = 0.25 d tout juste ; la réduire ne serait pas conservateur). Sinon, la
            # valeur bornée fait foi.
            st.session_state[cle_initiale] = bornee if dans_les_bornes else None

    valeur = conteneur.number_input(
        libelle.replace("{unite}", unite(nom_grandeur).replace("·", " \\cdot ")),
        min_value=borne_min,
        max_value=borne_max,
        step=kwargs.pop("step", pas),
        format=format_,
        key=cle_du_champ,
        **kwargs,
    )
    if valeur is None:
        st.session_state[cle_metrique] = None
    elif valeur != st.session_state.get(cle_initiale) or st.session_state.get(cle_metrique) is None:
        st.session_state[cle_metrique] = depuis_affichage(valeur, nom_grandeur)
        st.session_state[cle_initiale] = None  # modifiée : la valeur entrée fait foi
    return st.session_state[cle_metrique]


def _champ_imperial(
    libelle: str,
    nom_grandeur: str,
    key: str,
    conteneur,
    min_value: float | None,
    max_value: float | None,
    **kwargs,
) -> float | None:
    """
    Dimension (po) ou longueur (pi-po) en impérial : champ texte lu par unites.lire_imperial() (toutes les
    combinaisons de pieds, pouces et fractions de pouce), qui rend une valeur en mm. La valeur gardée est
    réaffichée au 1/16 po près (ex. « 3-1/2 », « 8 pi - 6 po »). Mêmes règles que champ() pour la bascule
    et les valeurs gardées (une valeur non modifiée reste exacte en mm).
    """
    longueur = nom_grandeur == "longueur"
    ecrire = ecrire_pieds_pouces if longueur else ecrire_pouces
    cle_du_champ, cle_de_l_autre, cle_metrique, cle_initiale = _cles(key, True)
    st.session_state.pop(cle_de_l_autre, None)
    if cle_du_champ not in st.session_state:
        metrique = st.session_state.get(cle_metrique)
        st.session_state[cle_du_champ] = "" if metrique is None else ecrire(metrique)
        st.session_state[cle_initiale] = st.session_state[cle_du_champ]

    aide = kwargs.pop("help", None)
    exemples = (
        "En pieds et pouces : ex. 8-6, 8' 6\", 3 pi 2-1/4 po, 8.5 (pieds) ou 6 po."
        if longueur else
        "En pouces : ex. 3.5, 3-1/2, 3 1/2, 3/4, ou en pieds et pouces : 1' 2-1/4\"."
    )
    for inutile in ("step", "format", "min_value", "max_value"):
        kwargs.pop(inutile, None)
    valeur = conteneur.text_input(
        libelle.replace("{unite}", _PI_PO if longueur else "po"),
        key=cle_du_champ,
        help=f"{aide} {exemples}" if aide else exemples,
        **kwargs,
    )
    if not valeur.strip():
        st.session_state[cle_metrique] = None
    elif valeur != st.session_state.get(cle_initiale) or st.session_state.get(cle_metrique) is None:
        try:
            pouces = lire_imperial(valeur, "pi" if longueur else "po")
        except ValueError:
            conteneur.error(f"Valeur illisible : « {valeur} ». {exemples}", icon=":material/error:")
            st.session_state[cle_metrique] = None
            return None
        st.session_state[cle_metrique] = vers_metrique(pouces, "dimension")  # po -> mm
        st.session_state[cle_initiale] = None  # modifiée : la valeur entrée fait foi
    metrique = st.session_state[cle_metrique]
    if metrique is not None:
        if min_value is not None and metrique < min_value:
            conteneur.error(
                f"La valeur doit être d'au moins {ecrire(min_value)}"
                + ("" if longueur else " po") + ".", icon=":material/error:"
            )
            return None
        if max_value is not None and metrique > max_value:
            conteneur.error(
                f"La valeur ne doit pas dépasser {vers_imperial(max_value, 'dimension'):.3f} po "
                f"({max_value:.1f} mm).", icon=":material/error:"
            )
            return None
    return metrique


def remplir(key: str, valeur_metrique: float | None) -> None:
    """
    Remplit un champ créé par champ() (ex. largeur d'appui préremplie avec la largeur de l'élément),
    dans les deux systèmes. À appeler avant d'afficher le champ.
    """
    st.session_state[f"_{key}__metrique"] = valeur_metrique
    st.session_state.pop(key, None)
    st.session_state.pop(f"{key}__imperial", None)
