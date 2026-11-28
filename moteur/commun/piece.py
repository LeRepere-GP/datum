"""
Pièce entrée en texte libre (retour LeRepere-GP/datum-retours#20) : lecture du texte seulement.

Une seule boîte « Pièce » remplace les anciens champs de la section « Matériaux » (bois vert, dimensions
brutes, largeur, hauteur et nombre de plis). Exemples de texte accepté :

    « 2x10 »                  1 pli, 2 x 10 po
    « 2 2x6 », « 2-2x6 »      2 plis de 2 x 6 po (aussi « 2 plis de 2x6 »)
    « 4x4 vert »              bois vert (teneur en humidité > 19 %)
    « 5 1/4 x 8 7/16 »        fractions de pouce (aussi « 5-1/4 x 8-7/16 », « 5.25 x 8.4375 »)
    « 2x6 brut »              dimensions brutes demandées par le mot « brut »
    « 89 x 140 mm »           millimètres : dimensions réelles
    « 2 38x235 mm »           2 plis de 38 x 235 mm

Ce module lit seulement le texte : il ne connaît pas la norme. Il rend les nombres entrés, l'unité et les
mots-clés. Le choix entre dimensions nominales, brutes ou réelles, et les dimensions nettes, viennent du
tableau A.3 (`tableau_A_3_..._du_bois_d_oeuvre.dimensions_de_la_piece()`).

Règles de lecture :
    - l'ordre est celui du texte : la 1re dimension est la largeur d'un pli (face étroite, d'où b), la 2e
      est la hauteur (d), comme dans les anciens champs ;
    - le nombre de plis (facultatif, 1 par défaut) est un entier au début, suivi d'une espace, d'un tiret
      ou du mot « plis » (« 2 2x6 », « 2-2x6 », « 2 plis de 2x6 ») ;
    - un entier suivi d'une fraction est un nombre fractionnaire, pas un nombre de plis : « 2 1/2 x 6 »
      et « 2-1/2 x 6 » valent 2.5 x 6 po (même écriture que l'affichage de Datum, ex. « 1-1/2 po ») ;
    - séparateur des dimensions : « x », « X », « × » ou « * » ;
    - décimales avec un point ou une virgule (« 5.25 » ou « 5,25 ») ;
    - unités : « po », « pouce(s) », « " » (par défaut) ou « mm », une seule unité pour toute la pièce ;
    - mots-clés : « vert » (ou « verte »), « sec » (par défaut, ou « sèche ») et « brut » (ou « brute ») ;
    - tout autre mot, une dimension nulle ou un texte d'une autre forme est refusé avec un message : jamais
      de valeur devinée (CLAUDE.md, « une erreur de calcul peut être dangereuse »).
"""

import re
from dataclasses import dataclass

# Nombre de plis permis : de 1 à 5, comme l'ancien choix « Élément composé (plis) » de l'interface. Ce
# n'est pas une limite de la norme : seulement celle de l'interface (et de la figure de la section).
NOMBRE_DE_PLIS_MAXIMAL = 5

# Mots reconnus (en minuscules, accents compris). Chaque mot a un seul sens.
_MOTS_VERT = {"vert", "verte", "verts", "vertes"}
_MOTS_SEC = {"sec", "seche", "sèche", "secs", "seches", "sèches"}
_MOTS_BRUT = {"brut", "brute", "bruts", "brutes"}
_MOTS_MM = {"mm"}
_MOTS_PO = {"po", "pouce", "pouces"}
_MOTS_PLIS = {"pli", "plis"}
_MOTS_DE_LIAISON = {"de"}  # « 2 plis de 2x6 »
_SEPARATEUR = "x"  # séparateur des dimensions (« × » et « * » sont changés en « x »)

# Nombre : entier suivi d'une fraction (« 5 1/4 », « 5-1/4 »), fraction seule (« 7/8 »), ou entier ou
# décimal (« 2 », « 5.25 »). Les fractionnaires sont essayés en premier.
_NOMBRE = r"\d+(?:\s*-\s*|\s+)\d+/\d+|\d+/\d+|\d+(?:\.\d+)?"
# Pièce : [plis + séparateur] largeur x hauteur. Le séparateur des plis (espace ou tiret) ne doit pas
# être suivi d'une fraction (« (?!\d+/) ») : « 2 1/2 x 6 » est un nombre fractionnaire, pas 2 plis.
_PIECE = re.compile(
    rf"(?:(?P<plis>\d+)\s*(?:-|\s)\s*(?!\d+/))?"
    rf"(?P<largeur>{_NOMBRE})\s*{_SEPARATEUR}\s*(?P<hauteur>{_NOMBRE})"
)


@dataclass(frozen=True)
class PieceEntree:
    """
    Ce que dit le texte de la pièce, sans interprétation de la norme.

    Args:
        texte (str): Texte entré, tel quel.
        nombre_de_plis (int): Nombre de plis (1 pour une pièce simple). Sans symbole dans la norme (un pli
            est un « élément individuel », 6.5.3.2.4).
        largeur_d_un_pli_entree (float): 1re dimension du texte : largeur d'un pli, po (mm si en_mm).
            Nominale ou brute selon le tableau A.3 ; ce n'est pas b (b = largeur totale, 3.2, issue #95).
        hauteur_entree (float): 2e dimension du texte : hauteur, po (mm si en_mm). Nominale ou brute ;
            ce n'est pas encore d (dimension nette, mm).
        texte_largeur (str): 1re dimension telle qu'écrite (ex. « 5 1/4 »), pour l'affichage.
        texte_hauteur (str): 2e dimension telle qu'écrite (ex. « 8 7/16 »), pour l'affichage.
        en_mm (bool): True si le texte est en millimètres (« mm ») : dimensions réelles.
        vert (bool): True si le mot « vert » est écrit (bois vert, teneur en humidité > 19 %).
        brut (bool): True si le mot « brut » est écrit.
    """

    texte: str
    nombre_de_plis: int
    largeur_d_un_pli_entree: float
    hauteur_entree: float
    texte_largeur: str
    texte_hauteur: str
    en_mm: bool
    vert: bool
    brut: bool


def _valeur_du_nombre(texte_du_nombre: str) -> float:
    """
    Valeur d'un nombre écrit comme dans _NOMBRE : « 5 1/4 » ou « 5-1/4 » -> 5.25 ; « 7/8 » -> 0.875 ;
    « 5.25 » -> 5.25 (sans unité : po ou mm selon le texte de la pièce).

    Raises:
        ValueError: Si une fraction a un dénominateur nul (ex. « 1/0 »).
    """
    # Un nombre fractionnaire est un entier, puis une fraction, séparés par une espace ou un tiret
    morceaux = re.split(r"\s*-\s*|\s+", texte_du_nombre.strip())
    valeur = 0.0
    for morceau in morceaux:
        if "/" in morceau:
            numerateur, denominateur = (int(n) for n in morceau.split("/"))
            if denominateur == 0:
                raise ValueError(f"la fraction « {morceau} » a un dénominateur nul")
            valeur += numerateur / denominateur
        else:
            valeur += float(morceau)
    return valeur


def lire_piece(texte: str) -> PieceEntree:
    """
    Lit le texte de la boîte « Pièce » (datum-retours #20), ex. « 2 2x6 », « 4x4 vert », « 5 1/4 x 8 7/16 »,
    « 89 x 140 mm ». Règles : voir la docstring du module.

    Args:
        texte (str): Texte entré.

    Returns:
        PieceEntree: Nombre de plis, les deux dimensions entrées (po, ou mm avec « mm »), l'unité et les
        mots-clés.

    Raises:
        ValueError: Si le texte est vide, contient un mot inconnu, deux unités, « vert » et « sec »
            ensemble, une dimension nulle, un nombre de plis hors de 1 à 5, ou n'a pas la forme
            « [plis] largeur x hauteur ». Le message donne la raison.
    """
    if not texte or not texte.strip():
        raise ValueError("entrez la pièce, ex. 2x6, 2 2x10, 4x4 vert, 5 1/4 x 8 7/16, 89 x 140 mm")

    # --- 1. Écritures équivalentes ramenées à une seule ---
    propre = texte.strip().lower()
    propre = propre.replace("×", " x ").replace("*", " x ")
    propre = propre.replace('"', " po ").replace("″", " po ")  # 5 1/4" = 5 1/4 po
    propre = re.sub(r"(?<=\d),(?=\d)", ".", propre)  # virgule décimale : 5,25 = 5.25
    # Lettres collées aux chiffres séparées (« 140mm » -> « 140 mm », « 2x6vert » -> « 2x6 vert »),
    # sauf le séparateur « x » seul entre deux nombres (« 2x6 »)
    propre = re.sub(r"(?<=\d)(?=[^\W\d_])(?!x(?:\s*\d))", " ", propre)
    propre = re.sub(r"(?<=[^\W\d_])(?=\d)(?<!x)", " ", propre)

    # --- 2. Mots-clés : retirés du texte et notés ---
    mots_trouves = set()
    for mot in re.findall(r"[^\W\d_]+", propre):
        if mot == _SEPARATEUR:
            continue  # séparateur des dimensions, lu à l'étape 3
        if mot not in (
            _MOTS_VERT | _MOTS_SEC | _MOTS_BRUT | _MOTS_MM | _MOTS_PO | _MOTS_PLIS | _MOTS_DE_LIAISON
        ):
            # Jamais de mot ignoré en silence : il pourrait changer le sens de la pièce (ex. « S-P-F »)
            raise ValueError(f"le mot « {mot} » n'est pas reconnu (mots permis : vert, sec, brut, mm, po)")
        mots_trouves.add(mot)
    vert = bool(mots_trouves & _MOTS_VERT)
    if vert and mots_trouves & _MOTS_SEC:
        raise ValueError("« vert » et « sec » sont écrits tous les deux : choisir l'un ou l'autre")
    en_mm = bool(mots_trouves & _MOTS_MM)
    if en_mm and mots_trouves & _MOTS_PO:
        raise ValueError("deux unités (mm et po) : écrire toute la pièce dans une seule unité")
    brut = bool(mots_trouves & _MOTS_BRUT)

    # Reste : les nombres et le séparateur (« 2 plis de 2x6 » -> « 2 2x6 »)
    reste = re.sub(r"[^\W\d_]+", lambda m: m.group() if m.group() == _SEPARATEUR else " ", propre)
    reste = re.sub(r"\s+", " ", reste).strip()

    # --- 3. Forme « [plis] largeur x hauteur » ---
    forme = _PIECE.fullmatch(reste)
    if forme is None:
        raise ValueError(
            f"« {reste} » n'a pas la forme [plis] largeur x hauteur (ex. 2x6, 2 2x10, 5 1/4 x 8 7/16)"
        )
    nombre_de_plis = int(forme["plis"]) if forme["plis"] else 1
    if not 1 <= nombre_de_plis <= NOMBRE_DE_PLIS_MAXIMAL:
        raise ValueError(f"le nombre de plis doit être de 1 à {NOMBRE_DE_PLIS_MAXIMAL} ({nombre_de_plis} entré)")
    largeur = _valeur_du_nombre(forme["largeur"])
    hauteur = _valeur_du_nombre(forme["hauteur"])
    if largeur <= 0 or hauteur <= 0:
        # Calculs de base : valeurs positives seulement (CLAUDE.md)
        raise ValueError("une dimension nulle n'est pas permise")

    return PieceEntree(
        texte=texte,
        nombre_de_plis=nombre_de_plis,
        largeur_d_un_pli_entree=largeur,
        hauteur_entree=hauteur,
        # Écriture d'origine, espaces simplifiés (« 5  1/4 » -> « 5 1/4 »)
        texte_largeur=re.sub(r"\s+", " ", forme["largeur"]),
        texte_hauteur=re.sub(r"\s+", " ", forme["hauteur"]),
        en_mm=en_mm,
        vert=vert,
        brut=brut,
    )
