"""
Bascule métrique / impérial de l'interface Streamlit (retour LeRepere-GP/datum-retours#10).

Tous les calculs se font en métrique (CLAUDE.md, ARCHITECTURE.md section 8). Ce module sert UNIQUEMENT à
l'affichage : il présente chaque champ et chaque résultat dans le système choisi dans la barre latérale,
et rend toujours au moteur des valeurs métriques (mm, kN, kN·m). Les conversions viennent de
moteur/commun/unites.py ; aucune formule de la norme ici.

Les dimensions nominales (ex. « 2x6 ») et les dimensions brutes restent en po dans les deux systèmes
(décision de l'utilisateur, retour #10).
"""

import math

import streamlit as st

from moteur.commun.nombres import cs
from moteur.commun.unites import grandeur, vers_imperial, vers_metrique

METRIQUE = "Métrique"
IMPERIAL = "Impérial"
SYSTEMES = (METRIQUE, IMPERIAL)

# Format et pas des champs, par grandeur et par système (unités de moteur/commun/unites.py)
_FORMAT_ET_PAS = {
    ("dimension", METRIQUE): ("%.0f", 1.0),  # mm
    ("dimension", IMPERIAL): ("%.2f", 0.25),  # po
    ("longueur", METRIQUE): ("%.0f", 100.0),  # mm
    ("longueur", IMPERIAL): ("%.2f", 0.5),  # pi
    ("force", METRIQUE): ("%.2f", 1.0),  # kN
    ("force", IMPERIAL): ("%.0f", 100.0),  # lb
    ("moment", METRIQUE): ("%.2f", 1.0),  # kN·m
    ("moment", IMPERIAL): ("%.0f", 1000.0),  # lb·po
}


def choisir_systeme() -> str:
    """
    Bascule « Unités » dans la barre latérale, gardée pour la séance (st.session_state["unites"]).
    Métrique par défaut.

    Returns:
        str: METRIQUE ou IMPERIAL.
    """
    st.sidebar.segmented_control(
        "Unités",
        options=SYSTEMES,
        default=METRIQUE,
        key="unites",
        width="stretch",
        help="""Unités des entrées et des résultats affichés. Les calculs se font toujours en
        métrique, comme dans la norme ; la note de calcul donne les deux unités.""",
    )
    return systeme()


def systeme() -> str:
    """Système d'unités choisi (METRIQUE si rien n'est choisi)."""
    return IMPERIAL if st.session_state.get("unites") == IMPERIAL else METRIQUE


def en_imperial() -> bool:
    """True si l'interface affiche l'impérial."""
    return systeme() == IMPERIAL


def unite(nom_grandeur: str) -> str:
    """Unité d'affichage de la grandeur dans le système choisi (ex. « mm » ou « po »)."""
    g = grandeur(nom_grandeur)
    return g.unite_imperiale if en_imperial() else g.unite_metrique


def vers_affichage(valeur_metrique: float, nom_grandeur: str) -> float:
    """Valeur métrique (unités de moteur/commun/unites.py) dans le système choisi."""
    return vers_imperial(valeur_metrique, nom_grandeur) if en_imperial() else valeur_metrique


def depuis_affichage(valeur: float, nom_grandeur: str) -> float:
    """Valeur du système choisi, ramenée en métrique pour le moteur."""
    return vers_metrique(valeur, nom_grandeur) if en_imperial() else valeur


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
    g = grandeur(nom_grandeur)
    if decimales is None:
        decimales = g.decimales_imperiale if en_imperial() else g.decimales_metrique
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
    Champ numérique dans le système choisi, qui rend une valeur métrique (ou None s'il est vide).

    La valeur entrée est gardée en métrique pour la séance : à la bascule, le champ affiche la même
    valeur dans l'autre système. Une valeur non modifiée après la bascule garde sa valeur métrique
    exacte (pas d'erreur d'arrondi : 89 mm -> 3.50 po -> 89 mm).

    En métrique, la clé du champ est `key` (tests et code existants) ; en impérial, `key + "__imperial"`.

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
    imperial = en_imperial()
    cle_du_champ = f"{key}__imperial" if imperial else key
    cle_de_l_autre = key if imperial else f"{key}__imperial"
    cle_metrique = f"_{key}__metrique"  # valeur métrique gardée pour la séance
    cle_initiale = f"_{key}__initiale"  # valeur affichée à la bascule (pour éviter la dérive d'arrondi)
    format_, pas = _FORMAT_ET_PAS[(nom_grandeur, systeme())]

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


def remplir(key: str, valeur_metrique: float | None) -> None:
    """
    Remplit un champ créé par champ() (ex. largeur d'appui préremplie avec la largeur de l'élément),
    dans les deux systèmes. À appeler avant d'afficher le champ.
    """
    st.session_state[f"_{key}__metrique"] = valeur_metrique
    st.session_state.pop(key, None)
    st.session_state.pop(f"{key}__imperial", None)
