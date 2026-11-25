"""
Calculatrice d'unités (issue #100) : un outil indépendant des calculs de la norme.

On y entre n'importe quel texte, avec des unités et des opérations, et elle donne le résultat dans
l'unité voulue, pour tout type d'unités (longueurs, aires, volumes, forces, moments, charges réparties,
pressions et contraintes, poids volumiques). Ex. « 8" x 600 mm en m² » = 0.12192 m².

Même principe que la saisie des champs (unites.lire_grandeur, PR #99), mais avec une analyse
dimensionnelle complète : chaque unité porte ses exposants de longueur et de force, et les produits sont
permis (« 3 pi * 4 pi » = 12 pi², « 5 kN * 2 m » = 10 kN·m). Les champs des calculs de la norme gardent
lire_grandeur() et ses vérifications (une aire reste refusée dans un champ de longueur).

Aucune formule de la norme ici. Unités de base des calculs : mm et N (donc N/mm² = MPa), comme dans les
normes. Facteurs exacts (définitions internationales) : 1 po = 25.4 mm ; 1 pi = 304.8 mm ;
1 lb (force) = 4.448 221 615 260 5 N. Aucun eval() : seuls les symboles décrits sont reconnus.
"""

import math
import re
from dataclasses import dataclass
from fractions import Fraction

from moteur.commun.unites import _JETON_NOMBRE, _LB_EN_N, _PI_EN_MM, _PO_EN_MM, normaliser_saisie

# Dimension : (exposant de la longueur, exposant de la force). Ex. (-2, 1) : force / longueur², une pression.
Dimension = tuple[int, int]

# Unités simples : motif -> (nombre de mm^a·N^b dans 1 unité, dimension). Les motifs sont en minuscules
# (le texte est mis en minuscules) ; le plus long est essayé en premier.
_KIP_EN_N = 1000 * _LB_EN_N
_UNITES: dict[str, tuple[float, Dimension]] = {
    # Longueurs
    r"mm": (1.0, (1, 0)),
    r"cm": (10.0, (1, 0)),
    r"m": (1000.0, (1, 0)),
    r"(?:po|pouces?|in(?:ch(?:es)?)?)": (_PO_EN_MM, (1, 0)),
    r"(?:pi|pieds?|ft|feet|foot)": (_PI_EN_MM, (1, 0)),
    r'"': (_PO_EN_MM, (1, 0)),
    r"'": (_PI_EN_MM, (1, 0)),
    # Forces
    r"n": (1.0, (0, 1)),
    r"kn": (1000.0, (0, 1)),
    r"(?:lbf|lbs|lb)": (_LB_EN_N, (0, 1)),
    r"(?:kips?|k)": (_KIP_EN_N, (0, 1)),
    # Pressions et contraintes (1 Pa = 1 N/m² = 1e-6 N/mm²)
    r"pa": (1e-6, (-2, 1)),
    r"kpa": (1e-3, (-2, 1)),
    r"mpa": (1.0, (-2, 1)),
    r"gpa": (1e3, (-2, 1)),
    r"psi": (_LB_EN_N / _PO_EN_MM**2, (-2, 1)),  # 4.448 N / 645.16 mm² = 0.006895 MPa
    r"ksi": (_KIP_EN_N / _PO_EN_MM**2, (-2, 1)),
    r"psf": (_LB_EN_N / _PI_EN_MM**2, (-2, 1)),  # 4.448 N / 92 903 mm² = 47.88 Pa
    r"ksf": (_KIP_EN_N / _PI_EN_MM**2, (-2, 1)),
    # Charges réparties
    r"plf": (_LB_EN_N / _PI_EN_MM, (-1, 1)),  # 4.448 N / 304.8 mm = 14.59 N/m
    r"klf": (_KIP_EN_N / _PI_EN_MM, (-1, 1)),
    # Poids volumiques
    r"pcf": (_LB_EN_N / _PI_EN_MM**3, (-3, 1)),  # 4.448 N / 28 316 847 mm³ = 0.1571 kN/m³
}
_LETTRES = tuple(sorted((m for m in _UNITES if m not in ('"', "'")), key=len, reverse=True))
_SYMBOLES = ('"', "'")
_PIEDS = r"(?:pi|pieds?|ft|feet|foot|')"
_EXPOSANTS = {"²": 2, "³": 3, "⁴": 4}

# Unités proposées à l'affichage, selon la dimension du résultat : (nom, unités ; métrique d'abord).
_AFFICHAGE: dict[Dimension, tuple[str, tuple[str, ...]]] = {
    (0, 0): ("nombre", ()),
    (1, 0): ("longueur", ("mm", "m", "po", "pi")),
    (2, 0): ("aire", ("mm²", "m²", "po²", "pi²")),
    (3, 0): ("volume ou module de section", ("mm³", "m³", "po³", "pi³")),
    (4, 0): ("moment d'inertie", ("mm⁴", "po⁴")),
    (0, 1): ("force", ("N", "kN", "lb", "kip")),
    (1, 1): ("moment", ("kN·m", "N·mm", "lb·po", "lb·pi", "kip·pi")),
    (-1, 1): ("charge répartie", ("kN/m", "N/mm", "lb/pi", "kip/pi")),
    (-2, 1): ("pression ou contrainte", ("kPa", "MPa", "psf", "psi", "ksi")),
    (-3, 1): ("poids volumique", ("kN/m³", "lb/pi³")),
}


class _Quantite:
    """
    Valeur en unités de base (mm^a·N^b), sa dimension (a, b), et le facteur de l'unité entrée (ex. 25.4
    pour « po »), qu'un nombre sans unité voisin d'une somme reprend (« 2 + 3 po » = 5 po).
    """

    __slots__ = ("valeur", "dimension", "facteur_de_saisie")

    def __init__(self, valeur: float, dimension: Dimension, facteur_de_saisie: float = 1.0):
        self.valeur, self.dimension, self.facteur_de_saisie = valeur, dimension, facteur_de_saisie


_SANS_DIMENSION: Dimension = (0, 0)


def _somme_des_dimensions(a: Dimension, b: Dimension, signe: int = 1) -> Dimension:
    return a[0] + signe * b[0], a[1] + signe * b[1]


def _nom_d_unite(dimension: Dimension) -> str:
    """Unité de base d'une dimension, pour les messages. Ex. (2, 0) -> « mm² » ; (-2, 1) -> « N/mm² »."""
    puissances = {1: "", 2: "²", 3: "³", 4: "⁴"}

    def ecrire(symbole: str, n: int) -> str:
        return symbole + puissances.get(n, f"^{n}")

    longueur, force = dimension
    haut = [ecrire(s, n) for s, n in (("N", force), ("mm", longueur)) if n > 0]
    bas = [ecrire(s, -n) for s, n in (("N", force), ("mm", longueur)) if n < 0]
    texte = "·".join(haut) or "1"
    return texte + ("/" + "·".join(bas) if bas else "") if (haut or bas) else "sans unité"


class _Lecteur:
    """
    Analyse d'une expression (descente récursive) : somme -> « sur » -> produit -> puissance -> unaire ->
    atome. Opérations : + - * / × ÷ · x ^ %, « sur », parenthèses ( ) et crochets [ ].

    Si unites_seulement, les nombres sont refusés : sert à lire une unité seule (« kN/m », « pi² »).
    """

    def __init__(self, texte: str, unites_seulement: bool = False):
        self.s, self.i, self.unites_seulement = texte, 0, unites_seulement
        self.apres_un_pourcentage = False

    # -- outils --
    def _espaces(self):
        while self.i < len(self.s) and self.s[self.i] == " ":
            self.i += 1

    def _voir(self) -> str:
        self._espaces()
        return self.s[self.i] if self.i < len(self.s) else ""

    def _mot(self, mot: str) -> bool:
        """Le mot (ex. « sur ») suit, seul : on le passe."""
        self._espaces()
        m = re.compile(rf"{mot}(?![a-z])").match(self.s, self.i)
        if m:
            self.i = m.end()
        return m is not None

    def _erreur(self):
        raise ValueError("texte illisible ou unité inconnue")

    def _unite(self):
        """Unité simple qui suit, avec son exposant (« m² », « m2 », « m^2 ») : (_Quantite, pieds) ou None."""
        self._espaces()
        for motif in _SYMBOLES + _LETTRES:
            m = re.compile(rf"(?:{motif})(?![a-z])").match(self.s, self.i)
            if not m:
                continue
            self.i = m.end()
            facteur, dimension = _UNITES[motif]
            exposant = 1
            if motif not in _SYMBOLES:  # « 8'2" » : le 2 est des pouces, pas un exposant
                e = re.compile(r"\^\s*([234])(?![\d.])|([²³⁴])|([234])(?![\d./])").match(self.s, self.i)
                if e:
                    self.i = e.end()
                    exposant = int(e.group(1) or e.group(3)) if not e.group(2) else _EXPOSANTS[e.group(2)]
            q = _Quantite(facteur**exposant, (dimension[0] * exposant, dimension[1] * exposant),
                          facteur**exposant)
            return q, exposant == 1 and re.fullmatch(_PIEDS, m.group(0)) is not None
        return None

    def _nombre(self):
        self._espaces()
        m = re.compile(_JETON_NOMBRE).match(self.s, self.i)
        if not m:
            return None
        if self.unites_seulement:
            self._erreur()
        self.i = m.end()
        texte = m.group(0)
        if "/" in texte:
            morceaux = texte.split()
            if any(x.endswith("/0") for x in morceaux):
                raise ValueError("division par zéro")
            return float(sum(Fraction(x) for x in morceaux))
        valeur = float(texte.replace(" ", ""))
        if not math.isfinite(valeur):
            raise ValueError("nombre trop grand")
        return valeur

    # -- grammaire --
    def lire(self) -> _Quantite:
        resultat = self._somme()
        if self._voir():
            self._erreur()
        return resultat

    def _somme(self) -> _Quantite:
        termes, signes = [self._sur()], [1]
        while self._voir() in ("+", "-"):
            signe = 1 if self.s[self.i] == "+" else -1
            self.i += 1
            termes.append(self._sur())
            signes.append(signe)
        if len(termes) == 1:
            return termes[0]
        # Même règle que les champs : un terme sans unité prend l'unité du terme suivant qui en a une
        # (« 2 + 3 po » = 5 po) ; sinon, celle du terme précédent.
        dimensions = {t.dimension for t in termes if t.dimension != _SANS_DIMENSION}
        if len(dimensions) > 1:
            raise ValueError("addition d'unités incompatibles")
        total = 0.0
        for k, (t, signe) in enumerate(zip(termes, signes)):
            if t.dimension == _SANS_DIMENSION and dimensions:
                voisin = next((u for u in termes[k + 1:] if u.dimension != _SANS_DIMENSION), None) or next(
                    u for u in reversed(termes[:k]) if u.dimension != _SANS_DIMENSION)
                total += signe * t.valeur * voisin.facteur_de_saisie
            else:
                total += signe * t.valeur
        return _Quantite(total, dimensions.pop() if dimensions else _SANS_DIMENSION)

    def _sur(self) -> _Quantite:
        """
        « A sur B » : A divisé par tout le produit B (« 400 lb sur 3 po x 3 1/4 po » = 400 lb / 9.75 po²).
        Priorité plus faible que * et /, plus forte que + et -.
        """
        gauche = self._produit()
        while self._mot("sur"):
            droite = self._produit()
            gauche = self._diviser(gauche, droite)
        return gauche

    @staticmethod
    def _diviser(gauche: _Quantite, droite: _Quantite) -> _Quantite:
        if droite.valeur == 0:
            raise ValueError("division par zéro")
        return _Quantite(gauche.valeur / droite.valeur,
                         _somme_des_dimensions(gauche.dimension, droite.dimension, -1),
                         gauche.facteur_de_saisie / droite.facteur_de_saisie)

    def _produit(self) -> _Quantite:
        gauche = self._puissance()
        while True:
            c = self._voir()
            m = re.compile(r"(?:de|of)(?![a-z])").match(self.s, self.i) if self.apres_un_pourcentage else None
            colle = 0 < self.i < len(self.s) - 1 and self.s[self.i - 1].isalpha() and self.s[self.i + 1].isalpha()
            if m:  # « 50% de 4 kN » = 2 kN
                self.i = m.end()
                operateur = "*"
            elif c in ("*", "×", "·") or (c in ("-", ".") and colle):  # « kN·m », « kN-m », « kN.m »
                operateur = "*"
                self.i += 1
            elif c in ("/", "÷"):
                operateur = "/"
                self.i += 1
            elif c == "x" and re.match(r"x\s*[-+\d.(\[\"'a-z]", self.s[self.i:]) and not re.match(
                    r"x[a-z]", self.s[self.i:]):
                operateur = "*"  # « x » : fois, devant un nombre, un signe, une parenthèse ou une unité
                self.i += 1
            else:
                break
            self.apres_un_pourcentage = False
            droite = self._puissance()
            if operateur == "/":
                gauche = self._diviser(gauche, droite)
            else:
                gauche = _Quantite(gauche.valeur * droite.valeur,
                                   _somme_des_dimensions(gauche.dimension, droite.dimension),
                                   gauche.facteur_de_saisie * droite.facteur_de_saisie)
        return gauche

    def _puissance(self) -> _Quantite:
        base = self._unaire()
        if self._voir() == "^":
            self.i += 1
            lecteur_d_exposant = self.unites_seulement
            self.unites_seulement = False
            exposant = self._unaire()
            self.unites_seulement = lecteur_d_exposant
            if exposant.dimension != _SANS_DIMENSION or exposant.valeur != int(exposant.valeur):
                raise ValueError("exposant invalide (nombre entier seulement)")
            n = int(exposant.valeur)
            try:
                valeur = base.valeur**n
                facteur = base.facteur_de_saisie**n
            except OverflowError:
                raise ValueError("nombre trop grand") from None
            except ZeroDivisionError:
                raise ValueError("division par zéro") from None
            if not math.isfinite(valeur):
                raise ValueError("nombre trop grand")
            base = _Quantite(valeur, (base.dimension[0] * n, base.dimension[1] * n), facteur)
        return base

    def _unaire(self) -> _Quantite:
        if self._voir() in ("-", "+"):
            signe = -1 if self.s[self.i] == "-" else 1
            self.i += 1
            q = self._unaire()
            return _Quantite(signe * q.valeur, q.dimension, q.facteur_de_saisie)
        return self._atome()

    def _atome(self) -> _Quantite:
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
                # Unité seule (« kN/m » : le « m » ; « 5 kN * m »)
                unite = self._unite()
                if unite is None:
                    self._erreur()
                self.apres_un_pourcentage = False
                return unite[0]
            q = _Quantite(valeur, _SANS_DIMENSION)
        self.apres_un_pourcentage = False
        if self._voir() == "%":
            self.i += 1
            q = _Quantite(q.valeur / 100, q.dimension, q.facteur_de_saisie)
            self.apres_un_pourcentage = True
        # Unité collée au nombre ou à la parenthèse : « 3 po », « (2 + 3) po »
        unite = self._unite() if q.dimension == _SANS_DIMENSION else None
        if unite is None:
            return q
        u, pieds = unite
        q = _Quantite(q.valeur * u.valeur, u.dimension, u.facteur_de_saisie)
        # Valeurs juxtaposées de même dimension, additionnées : « 8 pi 6 po », « 8' 6" », « 8 pi 6 »
        # (pouces après les pieds), « 3 pi 2 1/4 po »
        position = self.i
        suivant = self._nombre()
        if suivant is not None:
            unite_suivante = self._unite()
            if unite_suivante is None and pieds:
                unite_suivante = (_Quantite(_PO_EN_MM, (1, 0), _PO_EN_MM), False)
            if unite_suivante is None or unite_suivante[0].dimension != q.dimension:
                self.i = position
            else:
                v = unite_suivante[0]
                return _Quantite(q.valeur + suivant * v.valeur, q.dimension, v.facteur_de_saisie)
        return q


def _lire_unite(texte: str) -> _Quantite | None:
    """Unité seule (« kN/m », « pi² », « lb·pi »), ou None si le texte n'en est pas une."""
    if not texte or not re.search(r"[a-z\"']", texte):
        return None
    try:
        return _Lecteur(texte, unites_seulement=True).lire()
    except ValueError:
        return None


@dataclass(frozen=True)
class Calcul:
    """
    Résultat de la calculatrice d'unités.

    Args:
        valeur (float): Valeur en unités de base (mm^a·N^b ; ex. mm², N/mm² = MPa).
        dimension (Dimension): Exposants (longueur, force). Ex. (-2, 1) : une pression.
        unite_demandee (str | None): Unité écrite après « en » (ex. « m² »), ou None.
    """

    valeur: float
    dimension: Dimension
    unite_demandee: str | None = None

    @property
    def nom(self) -> str:
        """Nom de la dimension (ex. « aire »), ou l'unité de base si elle n'a pas de nom (ex. « N/mm⁴ »)."""
        return _AFFICHAGE[self.dimension][0] if self.dimension in _AFFICHAGE else _nom_d_unite(self.dimension)

    @property
    def unites_proposees(self) -> tuple[str, ...]:
        """Unités d'affichage offertes pour cette dimension (vide si la dimension n'a pas de nom)."""
        return _AFFICHAGE[self.dimension][1] if self.dimension in _AFFICHAGE else ()

    def dans(self, unite: str) -> float:
        """
        Valeur exprimée dans l'unité donnée (ex. « kPa », « lb/pi », « pi² »).

        Raises:
            ValueError: Si l'unité est inconnue ou n'a pas la même dimension que le résultat
                (ex. « mm² ne peut pas être affiché en pi »).
        """
        return self.valeur / _facteur_de_l_unite(unite, self.dimension)


def _facteur_de_l_unite(unite: str, dimension: Dimension) -> float:
    """Nombre d'unités de base dans 1 unité donnée, après avoir vérifié qu'elle a la dimension voulue."""
    q = _lire_unite(normaliser_saisie(unite))
    if q is None:
        raise ValueError(f"unité inconnue : {unite}")
    if q.dimension != dimension:
        raise ValueError(f"{_nom_d_unite(dimension)} ne peut pas être affiché en {unite}")
    return q.valeur


def calculer(texte: str) -> Calcul:
    """
    Calcule une expression avec unités, comme une calculatrice (issue #100).

    - Unités : longueurs (mm, cm, m, po, ", in, pi, ', ft), forces (N, kN, lb, kip, k), pressions et
      contraintes (Pa, kPa, MPa, GPa, psi, ksi, psf, ksf), charges réparties (plf, klf), poids volumiques
      (pcf), et toutes les unités composées : « kN/m », « kN·m », « lb/pi² », « N/mm² ».
    - Exposants d'une unité : « m² », « m2 », « m^2 » (2, 3 ou 4). « 8'2" » reste 8 pi 2 po.
    - Analyse dimensionnelle : « 3 pi * 4 pi » = 12 pi² ; « 5 kN * 2 m » = 10 kN·m ;
      « 3 po + 2 kN » est refusé.
    - Opérations : + - * / (aussi x, × et ÷), · (produit d'unités, aussi « - » ou « . » collés entre deux
      unités : « kN-m »), ^ (puissance entière), % (pourcentage ; « 50% de 4 kN »), parenthèses ( ) et [ ].
    - « sur » divise par tout le produit qui suit : « 400 lb sur 3 po x 3 1/4 po » = 400 lb / 9.75 po².
      Avec « / », l'ordre habituel s'applique (de gauche à droite) : « 400 lb / 3 po x 3 po » = 400 lb.
    - Unité de sortie : « en » ou « -> » à la fin : « 8" x 600 mm en m² ». Un « ? » ou un « = » à la
      fin est ignoré.
    - Comme dans les champs (lire_grandeur) : décimales avec un point ou une virgule, espaces de
      milliers, fractions (« 3 1/4 po »), pieds et pouces (« 8' 6" », « 8 pi 6 »), un nombre sans unité
      dans une somme prend l'unité voisine (« 2 + 3 po » = 5 po), et une unité à la toute fin
      s'applique au résultat si le reste n'a pas d'unité (« (2+3)/2 po » = 2.5 po).

    Exemples de l'utilisateur (issue #100) :
        « 8" x 600 mm en m² » = 203.2 mm x 600 mm = 121 920 mm² = 0.12192 m² ;
        « 400 lb sur 3 po x 3 1/4" en kPa » = 1779.29 N / 6290.31 mm² = 0.28286 MPa = 282.86 kPa.

    Args:
        texte (str): Expression entrée.

    Returns:
        Calcul: Valeur en unités de base, dimension et unité demandée.

    Raises:
        ValueError: Si le texte est illisible, si les unités sont incompatibles ou si l'unité demandée
            n'a pas la dimension du résultat. Le message donne la raison en quelques mots.
    """
    s = texte.strip().rstrip("?= ").strip()
    unite_demandee = None
    m = re.fullmatch(r"(.+?)\s*(?:(?<![a-z])en(?![a-z])|->|→)\s*(.+)", s, re.IGNORECASE)
    if m:
        s, unite_demandee = m.group(1), m.group(2).strip()  # unité gardée telle qu'écrite (messages)
        if _lire_unite(normaliser_saisie(unite_demandee)) is None:
            raise ValueError(f"unité inconnue : {unite_demandee}")
    s = normaliser_saisie(s)
    if not s:
        raise ValueError("valeur vide")
    try:
        resultat = None
        # Unité à la toute fin, reste sans unité : elle s'applique au résultat (« (2+3)/2 po »)
        for position in range(len(s) - 1, 0, -1):
            if s[position] not in "0123456789.)]% ":
                continue
            fin, reste = s[position + 1:].strip(), s[:position + 1].strip()
            unite = _lire_unite(fin)
            if unite is None:
                continue
            try:
                sans_unite = _Lecteur(reste).lire()
            except ValueError:
                continue
            if sans_unite.dimension == _SANS_DIMENSION:
                resultat = _Quantite(sans_unite.valeur * unite.valeur, unite.dimension)
            break
        if resultat is None:
            resultat = _Lecteur(s).lire()
    except ZeroDivisionError:
        raise ValueError("division par zéro") from None
    except OverflowError:
        raise ValueError("nombre trop grand") from None
    if not math.isfinite(resultat.valeur):
        raise ValueError("nombre trop grand")
    calcul = Calcul(resultat.valeur + 0.0, resultat.dimension, unite_demandee)
    if unite_demandee is not None:
        calcul.dans(unite_demandee)  # vérifie la dimension tout de suite
    return calcul
