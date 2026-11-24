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


# --- Saisie des valeurs : calculatrice avec unités (PR #99) ---
# Fonction générale, sans interface : reçoit le texte entré dans un champ (n'importe quelles unités, même
# mélangées, avec des opérations) et rend la valeur métrique utilisée dans les calculs (mm, kN, kN·m).
# Sert dans Streamlit aujourd'hui et servira dans la future interface web.

import math as _math  # noqa: E402
import re as _re  # noqa: E402
from fractions import Fraction as _Fraction  # noqa: E402

# Unités acceptées : nombre d'unités métriques de la famille (mm, kN, kN·m) dans 1 unité
_SEPARATEUR_DE_PRODUIT = r"(?:\s*[·*.\-]\s*|\s+|)"  # kN·m, kN*m, kN.m, kN-m, kN m, kNm
_UNITES_D_ENTREE = {
    "longueur": {
        r"mm": 1.0,
        r"cm": 10.0,
        r"m": 1000.0,
        r'(?:"|po|pouces?|in(?:ch(?:es)?)?)': _PO_EN_MM,
        r"(?:'|pi|pieds?|ft|feet|foot)": _PI_EN_MM,
    },
    "force": {
        r"n": 0.001,
        r"kn": 1.0,
        r"(?:lbf|lbs|lb)": _LB_EN_N / 1000,
        r"(?:kips?|k)": _LB_EN_N,
    },
    "moment": {
        rf"kn{_SEPARATEUR_DE_PRODUIT}mm": 1e-3,
        rf"kn{_SEPARATEUR_DE_PRODUIT}m": 1.0,
        rf"n{_SEPARATEUR_DE_PRODUIT}mm": 1e-6,
        rf"n{_SEPARATEUR_DE_PRODUIT}m": 1e-3,
        rf"(?:lbf|lbs|lb){_SEPARATEUR_DE_PRODUIT}(?:po|in)": _LB_EN_N * _PO_EN_MM / 1e6,
        rf"(?:lbf|lbs|lb){_SEPARATEUR_DE_PRODUIT}(?:pi|ft)": _LB_EN_N * _PI_EN_MM / 1e6,
        rf"(?:kips?|k){_SEPARATEUR_DE_PRODUIT}(?:po|in)": _LB_EN_N * _PO_EN_MM / 1e3,
        rf"(?:kips?|k){_SEPARATEUR_DE_PRODUIT}(?:pi|ft)": _LB_EN_N * _PI_EN_MM / 1e3,
    },
}
_FAMILLE = {"dimension": "longueur", "longueur": "longueur", "force": "force", "moment": "moment"}
_NOMS = {"dimension": "une dimension", "longueur": "une longueur", "force": "une force", "moment": "un moment"}
_PIEDS = r"(?:'|pi|pieds?|ft|feet|foot)"

# Nombres : espaces de milliers (« 40 000 »), nombre fractionnaire (« 2 1/4 »), fraction (« 3/4 »).
# Une fraction collée (« 3/4 ») est un seul nombre, sauf entre deux « / » (« 12/6/2 » = (12/6)/2).
_JETON_NOMBRE = (
    r"(?<![/\d.])\d+\s+\d+/\d+(?![\d/.])"  # 2 1/4
    r"|(?<![/\d.])\d+/\d+(?![\d/.])"  # 3/4
    r"|\d{1,3}(?:\s\d{3})+(?:\.\d+)?(?:e[+-]?\d+)?(?![\d/])"  # 40 000 ou 1 000.5
    r"|(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?"  # 3.5, .5, notation scientifique 1e3, 1.5e-3
)


class _Quantite:
    """
    Valeur métrique (mm, kN, kN·m) avec son exposant de dimension (0 : nombre pur ; 1 : la grandeur) et le
    facteur de l'unité entrée (ex. 25.4 pour « po »), qu'un nombre sans unité voisin d'une somme reprend
    (« 2 + 3 po » = 5 po).
    """

    __slots__ = ("valeur", "dimension", "facteur_de_saisie")

    def __init__(self, valeur: float, dimension: int, facteur_de_saisie: float = 1.0):
        self.valeur, self.dimension, self.facteur_de_saisie = valeur, dimension, facteur_de_saisie


class _Lecteur:
    """
    Analyse d'une expression (descente récursive) : somme -> produit -> puissance -> unaire -> atome.
    Opérations : + - * / × ÷ ^ %, parenthèses ( ) et crochets [ ]. Aucun eval() : seuls ces symboles sont
    reconnus.
    """

    def __init__(self, texte: str, famille: str, defaut: float):
        self.s, self.i, self.famille, self.defaut = texte, 0, famille, defaut
        self.apres_un_pourcentage = False  # « 50% de 4 » : « de » veut dire « fois » après un %
        unites = _UNITES_D_ENTREE[famille]
        self.unites = [(u, unites[u]) for u in sorted(unites, key=len, reverse=True)]

    # -- outils --
    def _espaces(self):
        while self.i < len(self.s) and self.s[self.i] == " ":
            self.i += 1

    def _voir(self) -> str:
        self._espaces()
        return self.s[self.i] if self.i < len(self.s) else ""

    def _erreur(self):
        raise ValueError(f"texte illisible, ou unité qui ne convient pas à {_NOMS[self.famille]}")

    def _unite(self):
        """Unité qui suit (facteur, est-ce des pieds), ou None."""
        self._espaces()
        for motif, facteur in self.unites:
            m = _re.compile(rf"(?:{motif})(?![a-z])").match(self.s, self.i)
            if m:
                self.i = m.end()
                return facteur, _re.fullmatch(_PIEDS, m.group(0)) is not None
        return None

    def _nombre(self):
        self._espaces()
        m = _re.compile(_JETON_NOMBRE).match(self.s, self.i)
        if not m:
            return None
        self.i = m.end()
        texte = m.group(0)
        if "/" in texte:
            morceaux = texte.split()
            if any(m.endswith("/0") for m in morceaux):
                raise ValueError("division par zéro")
            return float(sum(_Fraction(m) for m in morceaux))
        valeur = float(texte.replace(" ", ""))
        if not _math.isfinite(valeur):
            raise ValueError("nombre trop grand")  # ex. 1e400
        return valeur

    # -- grammaire --
    def lire(self) -> "_Quantite":
        resultat = self._somme()
        if self._voir():
            self._erreur()
        return resultat

    def _somme(self) -> "_Quantite":
        termes, signes = [self._produit()], [1]
        while self._voir() in ("+", "-"):
            signe = 1 if self.s[self.i] == "+" else -1
            self.i += 1
            termes.append(self._produit())
            signes.append(signe)
        if len(termes) == 1:
            return termes[0]
        # Un terme sans unité prend l'unité du terme suivant qui en a une (« 2 + 3 po » = 5 po) ; sinon,
        # celle du terme précédent ; un nombre pur seul reste un nombre pur.
        dimensions = {t.dimension for t in termes if t.dimension != 0}
        if len(dimensions) > 1:
            raise ValueError("addition d'unités incompatibles")
        total = 0.0
        for k, (t, signe) in enumerate(zip(termes, signes)):
            if t.dimension == 0 and dimensions:
                voisin = next((u for u in termes[k + 1:] if u.dimension), None) or next(
                    u for u in reversed(termes[:k]) if u.dimension)
                total += signe * t.valeur * voisin.facteur_de_saisie
            else:
                total += signe * t.valeur
        return _Quantite(total, dimensions.pop() if dimensions else 0)

    def _produit(self) -> "_Quantite":
        gauche = self._puissance()
        while True:
            c = self._voir()
            # « 50% de 4 » = 50% x 4 (demande de l'utilisateur) : « de » ou « of », seulement après un %
            m = _re.compile(r"(?:de|of)(?![a-z])").match(self.s, self.i) if self.apres_un_pourcentage else None
            if m:
                self.i = m.end()
                operateur = "*"
            elif c in ("*", "/", "×", "÷", "x"):
                operateur = c
                if operateur == "x" and not _re.match(r"x\s*[-+\d.(\[]", self.s[self.i:]):
                    break  # « x » seulement comme « fois » devant un nombre, un signe ou une parenthèse
                self.i += 1
            else:
                break
            self.apres_un_pourcentage = False
            droite = self._puissance()
            if operateur in ("/", "÷"):
                if droite.valeur == 0:
                    raise ValueError("division par zéro")
                gauche = _Quantite(gauche.valeur / droite.valeur, gauche.dimension - droite.dimension)
            elif gauche.dimension and droite.dimension:
                # « 2 po * 3 po » = 6 po (demande de l'utilisateur) : la même unité des deux côtés n'est
                # comptée qu'une fois. Deux unités différentes (« 2 po * 3 mm » : 6 po ou 6 mm ?) : refus.
                if (gauche.dimension, droite.dimension) != (1, 1) or not _math.isclose(
                        gauche.facteur_de_saisie, droite.facteur_de_saisie):
                    raise ValueError(
                        "multiplication de deux unités différentes : écrire l'unité une seule fois "
                        "(ex. 2 * 3 po)")
                gauche = _Quantite(gauche.valeur * droite.valeur / droite.facteur_de_saisie, 1,
                                   gauche.facteur_de_saisie)
            else:
                gauche = _Quantite(gauche.valeur * droite.valeur, gauche.dimension + droite.dimension,
                                   gauche.facteur_de_saisie if gauche.dimension else droite.facteur_de_saisie)
        return gauche

    def _puissance(self) -> "_Quantite":
        base = self._unaire()
        if self._voir() == "^":
            self.i += 1
            exposant = self._unaire()
            if exposant.dimension != 0 or exposant.valeur != int(exposant.valeur):
                raise ValueError("exposant invalide (nombre entier seulement)")
            try:
                valeur = base.valeur ** exposant.valeur
            except OverflowError:
                raise ValueError("nombre trop grand") from None
            except ZeroDivisionError:
                raise ValueError("division par zéro") from None
            if not _math.isfinite(valeur):
                raise ValueError("nombre trop grand")
            base = _Quantite(valeur, base.dimension * int(exposant.valeur))
        return base

    def _unaire(self) -> "_Quantite":
        if self._voir() in ("-", "+"):
            signe = -1 if self.s[self.i] == "-" else 1
            self.i += 1
            q = self._unaire()
            return _Quantite(signe * q.valeur, q.dimension, q.facteur_de_saisie)
        return self._atome()

    def _atome(self) -> "_Quantite":
        c = self._voir()
        if c in ("(", "["):
            fermeture = ")" if c == "(" else "]"
            self.i += 1
            q = self._somme()
            if self._voir() != fermeture:
                self._erreur()
            self.i += 1
        else:
            valeur = self._nombre()
            if valeur is None:
                self._erreur()
            q = _Quantite(valeur, 0)
        self.apres_un_pourcentage = False
        if self._voir() == "%":
            self.i += 1
            q = _Quantite(q.valeur / 100, q.dimension, q.facteur_de_saisie)
            self.apres_un_pourcentage = True
        # Unité collée au nombre ou à la parenthèse : « 3 po », « (2 + 3) po »
        unite = self._unite() if q.dimension == 0 else None
        if unite is None:
            return q
        facteur, pieds = unite
        q = _Quantite(q.valeur * facteur, 1, facteur)
        # Valeurs juxtaposées, additionnées : « 8 pi 38 mm », « 8' 6" », « 8 pi 6 » (pouces après les pieds)
        position = self.i
        suivant = self._nombre()
        if suivant is not None:
            unite_suivante = self._unite()
            if unite_suivante is None and pieds:
                unite_suivante = (_PO_EN_MM, False)
            if unite_suivante is None:
                self.i = position
            else:
                return _Quantite(q.valeur + suivant * unite_suivante[0], 1, unite_suivante[0])
        return q


def lire_grandeur(texte: str, nom_grandeur: str, imperial_par_defaut: bool = False) -> float:
    """
    Valeur entrée au clavier, comme dans une calculatrice, en unité métrique de la grandeur (mm, kN, kN·m).

    - Unités : longueurs (mm, cm, m, po, ", in, pi, ', ft), forces (N, kN, lb, kip), moments (kN·m, N·m,
      N·mm, lb·po, lb·pi, kip·pi, kip·po ; « · », « * », « . », « - » ou rien entre les deux).
    - Notation scientifique : « 1e3 mm », « 1.5E-3 m », « 2,5e4 N » (demande de l'utilisateur).
    - Décimales avec un point ou une virgule (« 3.5 » = « 3,5 ») ; la virgule est toujours décimale, même
      suivie de 3 chiffres (« 1,500 » = 1.5, décision de l'utilisateur). Milliers : une espace (« 40 000 »).
    - Opérations : + - * / (aussi x, × et ÷), ^ (puissance entière), % (pourcentage), parenthèses ( ) et [ ].
      « x » est une multiplication (demande de l'utilisateur) : « 2 x 3 po » = « 2x3 po » = 6 po.
      « de » (ou « of ») après un pourcentage veut dire « fois » : « 50% de 4 » = 2.
      « - » est toujours une soustraction (décision de l'utilisateur) : « 8-6 » = 2.
    - Pieds, pouces et fractions : « 8' 6" », « 8 pi 6 po », « 8 pi 6 » (pouces après les pieds),
      « 3 pi 2 1/4 po », « 1/2 po », « 2 1/4" ».
    - Valeurs juxtaposées additionnées : « 8 pi 38 mm » = 2438.4 mm + 38 mm = 2476.4 mm.
    - Un nombre sans unité dans une somme prend l'unité du terme suivant (« 2 + 3 po » = 5 po).
    - Une unité à la toute fin s'applique au résultat si le reste n'a pas d'unité (décision de
      l'utilisateur) : « (2+3)/2 po » = 2 1/2 po, « 3*4 kN » = 12 kN.
    - Un résultat sans unité prend l'unité par défaut : métrique (mm, kN, kN·m) ou impériale (po pour une
      dimension, pi pour une longueur, lb, lb·po), selon imperial_par_defaut. « (2+3)/2 » = 2.5.
    - Multiplication : la même unité des deux côtés n'est comptée qu'une fois (« 2 po * 3 po » = 6 po,
      demande de l'utilisateur) ; deux unités différentes (« 2 po * 3 mm ») sont refusées.
    - Les unités sont vérifiées : « 5 kN » dans un champ de longueur ou « 3 po + 2 kN » sont refusés.

    Exemple de l'utilisateur : « 8 pieds + 36 po - 50 mm » = 2438.4 mm + 914.4 mm - 50 mm = 3302.8 mm.

    Args:
        texte (str): Texte entré.
        nom_grandeur (str): « dimension », « longueur », « force » ou « moment ».
        imperial_par_defaut (bool, optional): Unité par défaut impériale. Default to False (métrique).

    Returns:
        float: Valeur en mm, kN ou kN·m.

    Raises:
        ValueError: Si le texte est illisible, si les unités ne conviennent pas ou si la grandeur n'est
            pas offerte. Le message donne la raison en quelques mots (ex. « le résultat n'est pas une
            longueur »), pour l'interface.
    """
    if nom_grandeur not in _FAMILLE:
        raise ValueError(f"Saisie libre non offerte pour la grandeur {nom_grandeur!r}.")
    famille = _FAMILLE[nom_grandeur]
    s = (texte.strip().lower().replace(",", ".").replace("’", "'").replace("′", "'")
         .replace("”", '"').replace("″", '"').replace("''", '"').replace(" ", " ")
         .replace(" ", " ").replace("−", "-").replace("\t", " "))
    if not s:
        raise ValueError("valeur vide")
    if imperial_par_defaut:
        defaut = {"longueur": _PI_EN_MM if nom_grandeur == "longueur" else _PO_EN_MM,
                  "force": _LB_EN_N / 1000, "moment": _LB_EN_N * _PO_EN_MM / 1e6}[famille]
    else:
        defaut = 1.0
    try:
        # Unité à la toute fin, reste sans unité : elle s'applique au résultat (« (2+3)/2 po »)
        lecteur = _Lecteur(s, famille, defaut)
        for position in range(len(s) - 1, -1, -1):
            if s[position] in "0123456789.)]% ":
                fin = s[position + 1:].strip()
                reste = s[:position + 1].strip()
                if fin and _re.fullmatch("|".join(f"(?:{u})" for u, _ in lecteur.unites), fin):
                    facteur = next(f for u, f in lecteur.unites if _re.fullmatch(u, fin))
                    try:
                        sans_unite = _Lecteur(reste, famille, defaut).lire()
                    except ValueError:
                        break
                    if sans_unite.dimension == 0:
                        return sans_unite.valeur * facteur
                break
        resultat = lecteur.lire()
    except ValueError:
        raise
    except ZeroDivisionError:
        raise ValueError("division par zéro") from None
    except OverflowError:
        raise ValueError("nombre trop grand") from None
    if resultat.dimension != 0 and resultat.dimension != 1:
        raise ValueError(f"le résultat n'est pas {_NOMS[nom_grandeur]}")
    valeur = resultat.valeur * (defaut if resultat.dimension == 0 else 1.0)
    if not _math.isfinite(valeur):
        raise ValueError("nombre trop grand")  # ex. 1e308 * 10
    return valeur + 0.0  # « -0 » -> 0.0 (pas de « -0.00 kN » à l'affichage)


# --- Écriture des longueurs impériales (affichage) ---

def _seiziemes(valeur_metrique: float) -> int:
    """Longueur en mm, en seizièmes de pouce (arrondie au 1/16 po près ; 1 po = 25.4 mm)."""
    return round(valeur_metrique / _PO_EN_MM * 16)


def _pouces_et_fraction(seiziemes: int) -> str:
    """191 seizièmes -> « 11 15/16 » ; 8 -> « 1/2 » ; 48 -> « 3 ». Sans tiret (« - » = soustraction)."""
    signe = "-" if seiziemes < 0 else ""
    entiers, reste = divmod(abs(seiziemes), 16)
    if not reste:
        return f"{signe}{entiers}"
    fraction = _Fraction(reste, 16)
    return f"{signe}{entiers} {fraction}" if entiers else f"{signe}{fraction}"


def ecrire_pouces(valeur_metrique: float) -> str:
    """
    Longueur métrique (mm) en pouces et fraction de pouce, au 1/16 po près, sans l'unité.
    Ex. 88.9 mm -> « 3 1/2 » ; 38 mm -> « 1 1/2 » ; 19.05 mm -> « 3/4 ».
    """
    return _pouces_et_fraction(_seiziemes(valeur_metrique))


def ecrire_pieds_pouces(valeur_metrique: float) -> str:
    """
    Longueur métrique (mm) en pieds et pouces, au 1/16 po près. Ex. 2590.8 mm -> « 8 pi 6 po » ;
    971.55 mm -> « 3 pi 2 1/4 po ». Le texte se relit avec lire_grandeur() (sans tiret).
    """
    pieds, seiziemes = divmod(_seiziemes(valeur_metrique), 12 * 16)
    return f"{pieds} pi {_pouces_et_fraction(seiziemes)} po"
