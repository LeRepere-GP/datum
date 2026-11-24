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
dans l'autre système. Les longueurs en impérial s'entrent en pieds et pouces (ex. « 8-6 » = 8 pi 6 po).

Les dimensions nominales (ex. « 2x6 ») et les dimensions brutes restent en po dans les deux systèmes
(décision de l'utilisateur, retour #10).
"""

import math
import re
from fractions import Fraction

import streamlit as st

from moteur.commun.nombres import cs
from moteur.commun.unites import grandeur, vers_imperial, vers_metrique

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
# Les longueurs en impérial s'entrent en pieds-pouces (champ texte, voir _champ_pieds_pouces()).
_FORMAT_ET_PAS = {
    ("dimension", METRIQUE): ("%.0f", 1.0),  # mm
    ("dimension", IMPERIAL): ("%.2f", 0.25),  # po
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


# --- Pieds et pouces ---

_NOMBRE = r"\d+(?:\.\d+)?"
# Pouces : 6, 6.5, 6 1/2, 6-1/2 ou 1/2 (fractions de pouce, demande de l'utilisateur)
_POUCES = rf"(?:{_NOMBRE}(?:(?:\s+|\s*-\s*)\d+/\d+)?|\d+/\d+)"
_UNITE_PI = r"(?:'|pi|pieds?)"
_UNITE_PO = r'(?:"|po|pouces?)'


def _pouces(texte: str) -> float:
    """« 6 1/2 » ou « 6-1/2 » -> 6.5 ; « 1/2 » -> 0.5 ; « 6.5 » -> 6.5."""
    total = 0.0
    for morceau in texte.replace("-", " ").split():
        if "/" in morceau:
            numerateur, denominateur = morceau.split("/")
            if float(denominateur) == 0:
                raise ValueError("division par zéro")
            total += float(numerateur) / float(denominateur)
        else:
            total += float(morceau)
    return total


def lire_pieds_pouces(texte: str) -> float:
    """
    Longueur entrée en pieds et pouces, en pieds.

    Formes acceptées (point décimal ou virgule) : « 8-6 », « 8 - 6 », « 8 6 », « 8'-6" », « 8' 6" »,
    « 8 pi 6 po », « 8 pi - 6 1/2 po », « 3 pi 2-1/4 po », « 3-2-1/4 », « 8.5 » ou « 8 pi » (pieds
    seulement), « 6 po », « 6" » ou « 2-1/4 po » (pouces seulement, l'unité est alors obligatoire).
    Sans unité, « 3-1/4 » se lit 3 pi 1/4 po ; avec l'unité, « 3-1/4 po » se lit 3 1/4 po.

    Raises:
        ValueError: Si le texte n'est pas une longueur en pieds et pouces.
    """
    s = (texte.strip().lower().replace(",", ".").replace("’", "'").replace("′", "'")
         .replace("”", '"').replace("″", '"').replace("''", '"'))
    if not s:
        raise ValueError("vide")
    # Pouces seulement : l'unité est obligatoire (« 6 1/2 po »)
    m = re.fullmatch(rf"(?P<po>{_POUCES})\s*{_UNITE_PO}", s)
    if m:
        return _pouces(m["po"]) / 12
    # Pieds seulement : « 8.5 », « 8 pi », « 8' »
    m = re.fullmatch(rf"(?P<pi>{_NOMBRE})\s*{_UNITE_PI}?", s)
    if m:
        return float(m["pi"])
    # Pieds et pouces : « 8-6 », « 8' 6" », « 8 pi - 6 1/2 po »
    m = re.fullmatch(
        rf"(?P<pi>{_NOMBRE})\s*(?:{_UNITE_PI}\s*-?\s*|-\s*|\s+)(?P<po>{_POUCES})\s*{_UNITE_PO}?", s
    )
    if m:
        return float(m["pi"]) + _pouces(m["po"]) / 12
    raise ValueError(f"longueur illisible : « {texte} »")


def ecrire_pieds_pouces(valeur_metrique: float) -> str:
    """
    Longueur métrique (mm) en pieds et pouces, au 1/16 po près. Ex. 2590.8 mm -> « 8 pi - 6 po » ;
    971.55 mm -> « 3 pi - 2-1/4 po ».
    """
    seiziemes = round(valeur_metrique / 25.4 * 16)  # 1 po = 25.4 mm
    pieds, seiziemes = divmod(seiziemes, 12 * 16)
    entiers, reste = divmod(seiziemes, 16)
    pouces = str(entiers)
    if reste:
        fraction = Fraction(reste, 16)
        pouces = f"{entiers}-{fraction}" if entiers else f"{fraction}"
    return f"{pieds} pi - {pouces} po"


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
    Les longueurs en impérial s'entrent en pieds-pouces (champ texte, ex. « 8-6 »).

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
    if nom_grandeur == "longueur" and imperial:
        return _champ_pieds_pouces(libelle, key, conteneur, min_value, max_value, **kwargs)
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


def _champ_pieds_pouces(
    libelle: str,
    key: str,
    conteneur,
    min_value: float | None,
    max_value: float | None,
    **kwargs,
) -> float | None:
    """
    Longueur en impérial : champ texte en pieds et pouces (ex. « 8-6 » = 8 pi 6 po = 8.5 pi), qui rend
    une valeur en mm. Mêmes règles que champ() pour la bascule et les valeurs gardées.
    """
    cle_du_champ, cle_de_l_autre, cle_metrique, cle_initiale = _cles(key, True)
    st.session_state.pop(cle_de_l_autre, None)
    if cle_du_champ not in st.session_state:
        metrique = st.session_state.get(cle_metrique)
        st.session_state[cle_du_champ] = "" if metrique is None else ecrire_pieds_pouces(metrique)
        st.session_state[cle_initiale] = st.session_state[cle_du_champ]

    aide = kwargs.pop("help", None)
    exemples = "En pieds et pouces : ex. 8-6, 8' 6\", 3 pi 2-1/4 po, 8.5 (pieds) ou 6 po."
    for inutile in ("step", "format", "min_value", "max_value"):
        kwargs.pop(inutile, None)
    valeur = conteneur.text_input(
        libelle.replace("{unite}", _PI_PO),
        key=cle_du_champ,
        help=f"{aide} {exemples}" if aide else exemples,
        **kwargs,
    )
    if not valeur.strip():
        st.session_state[cle_metrique] = None
    elif valeur != st.session_state.get(cle_initiale) or st.session_state.get(cle_metrique) is None:
        try:
            metrique = vers_metrique(lire_pieds_pouces(valeur), "longueur")
        except ValueError:
            conteneur.error(
                f"Longueur illisible : « {valeur} ». {exemples}", icon=":material/error:"
            )
            st.session_state[cle_metrique] = None
            return None
        st.session_state[cle_metrique] = metrique
        st.session_state[cle_initiale] = None  # modifiée : la valeur entrée fait foi
    metrique = st.session_state[cle_metrique]
    if metrique is not None and (
        (min_value is not None and metrique < min_value)
        or (max_value is not None and metrique > max_value)
    ):
        conteneur.error("Longueur hors des limites permises.", icon=":material/error:")
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
