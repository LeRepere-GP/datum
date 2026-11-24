"""
Unités : conversions entre le métrique et l'impérial.

Tous les calculs se font en métrique, comme dans les normes. Ces conversions servent UNIQUEMENT à
l'affichage des entrées et des résultats pour l'utilisateur (ARCHITECTURE.md, section 8).

Facteurs exacts (définitions internationales) :
    1 po = 25,4 mm ; 1 pi = 304,8 mm ; 1 lb (force) = 4,448 221 615 260 5 N.
"""

from dataclasses import dataclass

_LB_EN_N = 4.4482216152605
_PO_EN_MM = 25.4
_PI_EN_MM = 304.8


@dataclass(frozen=True)
class Grandeur:
    """
    Une grandeur physique avec son unité métrique et son unité impériale d'affichage.

    Args:
        unite_metrique (str): Unité métrique d'affichage (ex. "kN").
        unite_imperiale (str): Unité impériale d'affichage (ex. "lb").
        facteur (float): Nombre d'unités métriques dans 1 unité impériale.
        decimales_metrique (int): Décimales à l'affichage en métrique.
        decimales_imperiale (int): Décimales à l'affichage en impérial.
    """

    unite_metrique: str
    unite_imperiale: str
    facteur: float
    decimales_metrique: int
    decimales_imperiale: int


GRANDEURS: dict[str, Grandeur] = {
    # Dimensions d'une section (b, d, longueur d'appui...) : mm et po
    "dimension": Grandeur("mm", "po", _PO_EN_MM, 0, 2),
    # Longueurs d'un élément (L, L_e...) : mm et pi
    "longueur": Grandeur("mm", "pi", _PI_EN_MM, 0, 2),
    # Aires : mm² et po²
    "aire": Grandeur("mm²", "po²", _PO_EN_MM**2, 0, 2),
    # Forces : kN et lb
    "force": Grandeur("kN", "lb", _LB_EN_N / 1000, 2, 0),
    # Moments : kN·m et lb·po (préférence de l'utilisateur)
    "moment": Grandeur("kN·m", "lb·po", _LB_EN_N * _PO_EN_MM / 1e6, 2, 0),
    # Contraintes et résistances prévues : MPa et psi
    "contrainte": Grandeur("MPa", "psi", _LB_EN_N / _PO_EN_MM**2, 2, 0),
}


def grandeur(nom: str) -> Grandeur:
    """
    Retourne la grandeur demandée.

    Raises:
        KeyError: Si la grandeur n'existe pas.
    """
    if nom not in GRANDEURS:
        raise KeyError(f"Grandeur inconnue : {nom!r}. Choix : {sorted(GRANDEURS)}.")
    return GRANDEURS[nom]


def vers_imperial(valeur: float, nom_grandeur: str) -> float:
    """Convertit une valeur métrique (unité d'affichage) en impérial."""
    return valeur / grandeur(nom_grandeur).facteur


def vers_metrique(valeur: float, nom_grandeur: str) -> float:
    """Convertit une valeur impériale en métrique (unité d'affichage)."""
    return valeur * grandeur(nom_grandeur).facteur


def deux_unites(valeur: float, nom_grandeur: str) -> str:
    """
    Formate une valeur métrique avec son équivalent impérial, pour la note de calcul.

    Exemple : deux_unites(38, "dimension") -> "38 mm (1.50 po)".
    Le point est utilisé comme séparateur décimal.
    """
    g = grandeur(nom_grandeur)
    imperial = vers_imperial(valeur, nom_grandeur)
    return (
        f"{valeur:.{g.decimales_metrique}f} {g.unite_metrique} "
        f"({imperial:.{g.decimales_imperiale}f} {g.unite_imperiale})"
    )


# --- Longueurs impériales en pieds, pouces et fractions de pouce (PR #99) ---
# Fonctions générales, sans interface : servent à toute entrée ou tout affichage en impérial (dimensions
# en po, longueurs en pi-po), dans Streamlit aujourd'hui et dans la future interface web.

import re as _re  # noqa: E402
from fractions import Fraction as _Fraction  # noqa: E402

_NOMBRE = r"\d+(?:\.\d+)?"
# Pouces : 6, 6.5, 6 1/2, 6-1/2 ou 1/2
_POUCES = rf"(?:{_NOMBRE}(?:(?:\s+|\s*-\s*)\d+/\d+)?|\d+/\d+)"
_UNITE_PI = r"(?:'|pi|pieds?)"
_UNITE_PO = r'(?:"|po|pouces?)'


def _valeur_des_pouces(texte: str) -> float:
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


def lire_imperial(texte: str, unite_par_defaut: str = "po") -> float:
    """
    Longueur impériale entrée au clavier, en pouces. Toutes les combinaisons de pieds, de pouces et de
    fractions de pouce sont acceptées (point décimal ou virgule, apostrophes droites ou typographiques) :

    - pieds et pouces : « 8-6 », « 8 - 6 », « 8 6 », « 8'-6" », « 8' 6" », « 8 pi 6 po »,
      « 3 pi 2-1/4 po », « 3'-2 1/4" », « 3-2-1/4 » ;
    - pieds seulement : « 8 pi », « 8' » ;
    - pouces seulement : « 6 po », « 6" », « 2-1/4 po », « 3/4" » ;
    - nombre sans unité (« 8.5 », « 3-1/2 », « 3 1/2 », « 3/4 ») : dans l'unité par défaut du champ.
      Pour un champ en pieds (unite_par_defaut="pi"), « 3-1/4 » se lit 3 pi 1/4 po (notation des plans).

    Exemple : lire_imperial("3 pi 2-1/4 po") -> 38.25 (po) ; x 25.4 mm/po = 971.55 mm.

    Args:
        texte (str): Texte entré.
        unite_par_defaut (str, optional): « po » ou « pi », pour un nombre sans unité. Default to "po".

    Returns:
        float: Longueur en pouces.

    Raises:
        ValueError: Si le texte n'est pas une longueur impériale, ou si l'unité par défaut est inconnue.
    """
    if unite_par_defaut not in ("po", "pi"):
        raise ValueError(f"Unité par défaut inconnue : {unite_par_defaut!r} (« po » ou « pi »).")
    s = (texte.strip().lower().replace(",", ".").replace("’", "'").replace("′", "'")
         .replace("”", '"').replace("″", '"').replace("''", '"'))
    if not s:
        raise ValueError("Longueur vide.")
    # Pouces seulement, avec l'unité : « 6 po », « 2-1/4" »
    m = _re.fullmatch(rf"(?P<po>{_POUCES})\s*{_UNITE_PO}", s)
    if m:
        return _valeur_des_pouces(m["po"])
    # Pieds seulement, avec l'unité : « 8 pi », « 8' »
    m = _re.fullmatch(rf"(?P<pi>{_NOMBRE})\s*{_UNITE_PI}", s)
    if m:
        return float(m["pi"]) * 12
    # Nombre sans unité, dans l'unité par défaut
    if unite_par_defaut == "po":
        if _re.fullmatch(_POUCES, s):
            return _valeur_des_pouces(s)
    elif _re.fullmatch(_NOMBRE, s):
        return float(s) * 12
    # Pieds et pouces : « 8-6 », « 8' 6" », « 3 pi - 2-1/4 po »
    m = _re.fullmatch(
        rf"(?P<pi>{_NOMBRE})\s*(?:{_UNITE_PI}\s*-?\s*|-\s*|\s+)(?P<po>{_POUCES})\s*{_UNITE_PO}?", s
    )
    if m:
        return float(m["pi"]) * 12 + _valeur_des_pouces(m["po"])
    raise ValueError(f"Longueur illisible : « {texte} ».")


def _seiziemes(valeur_metrique: float) -> int:
    """Longueur en mm, en seizièmes de pouce (arrondie au 1/16 po près ; 1 po = 25.4 mm)."""
    return round(valeur_metrique / _PO_EN_MM * 16)


def _pouces_et_fraction(seiziemes: int) -> str:
    """191 seizièmes -> « 11-15/16 » ; 8 -> « 1/2 » ; 48 -> « 3 »."""
    entiers, reste = divmod(seiziemes, 16)
    if not reste:
        return str(entiers)
    fraction = _Fraction(reste, 16)
    return f"{entiers}-{fraction}" if entiers else f"{fraction}"


def ecrire_pouces(valeur_metrique: float) -> str:
    """
    Longueur métrique (mm) en pouces et fraction de pouce, au 1/16 po près, sans l'unité.
    Ex. 88.9 mm -> « 3-1/2 » ; 38 mm -> « 1-1/2 » ; 19.05 mm -> « 3/4 ».
    """
    return _pouces_et_fraction(_seiziemes(valeur_metrique))


def ecrire_pieds_pouces(valeur_metrique: float) -> str:
    """
    Longueur métrique (mm) en pieds et pouces, au 1/16 po près. Ex. 2590.8 mm -> « 8 pi - 6 po » ;
    971.55 mm -> « 3 pi - 2-1/4 po ».
    """
    pieds, seiziemes = divmod(_seiziemes(valeur_metrique), 12 * 16)
    return f"{pieds} pi - {_pouces_et_fraction(seiziemes)} po"
