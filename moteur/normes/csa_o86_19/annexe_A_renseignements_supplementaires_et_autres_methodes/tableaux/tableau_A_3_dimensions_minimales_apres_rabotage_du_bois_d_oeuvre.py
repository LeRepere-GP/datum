"""
CSA O86:19 - Tableau A.3 Dimensions minimales après rabotage du bois d'œuvre (annexe A, p. 302-303).

Voir 6.5.2 : dimensions nettes du bois sec (6.5.2.1) ou vert (6.5.2.2), arrondies au millimètre près.

Décisions validées avec l'utilisateur (CLAUDE.md) :
    - Dimensions nominales offertes : 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14 et 16 po.
    - 7 et 9 po : seulement pour le gros bois vert (165 et 216 mm).
    - Gros bois (face étroite >= 5 po nominal) vert : dimensions du gros bois du tableau A.3.
    - Mode « dimensions brutes » : convention de l'utilisateur (hors tableau A.3), conservée telle quelle.
    - Pièce en texte libre (datum-retours #20) : voir dimensions_de_la_piece().
"""

from dataclasses import dataclass

from moteur.commun.piece import PieceEntree
from moteur.normes.csa_o86_19.base_de_donnees import lire

_PO_EN_MM = 25.4


def _ligne(nominale: float):
    lignes = lire("SELECT * FROM lumber_sizes WHERE nominal = ?", (nominale,))
    return lignes[0] if lignes else None


def dimensions_nominales() -> list[int]:
    """
    Tableau A.3 Dimensions nominales offertes, po (bois de dimension et gros bois).

    Returns:
        list[int]: Dimensions nominales, po.
    """
    lignes = lire(
        "SELECT nominal FROM lumber_sizes "
        "WHERE dry IS NOT NULL OR green_timber IS NOT NULL ORDER BY nominal"
    )
    return [ligne["nominal"] for ligne in lignes]


def est_gros_bois(b_nominale: float, d_nominale: float) -> bool:
    """
    Tableau A.3 Gros bois : face étroite de 114 mm (5 po nominal) ou plus.

    Args:
        b_nominale (float): Largeur nominale, po.
        d_nominale (float): Hauteur nominale, po.

    Returns:
        bool: True si l'élément est du gros bois.
    """
    return min(b_nominale, d_nominale) >= 5


def dimension_nette(
    nominale: float,
    vert: bool = False,
    brut: bool = False,
    gros_bois: bool = False,
) -> int:
    """
    Tableau A.3 Dimension nette (minimale après rabotage), mm.

    Args:
        nominale (float): Dimension nominale, po (dimension réelle, po, en mode brut).
        vert (bool, optional): Bois vert (teneur en humidité > 19 %). Default to False.
        brut (bool, optional): Dimensions brutes (convention de l'utilisateur). Default to False.
        gros_bois (bool, optional): Gros bois (voir est_gros_bois). En vert, dimensions du gros
            bois du tableau A.3. Default to False.

    Returns:
        int: Dimension nette, mm.

    Raises:
        ValueError: Si la dimension nominale n'est pas au tableau A.3 (hors mode brut).
    """
    ligne = _ligne(nominale)

    if brut:
        if ligne is None:
            return int(round(nominale * _PO_EN_MM))
        return ligne["green_brut"] if vert else ligne["dry_brut"]

    if ligne is None:
        raise ValueError(
            f"La dimension nominale {nominale} po n'est pas offerte (tableau A.3). "
            f"Dimensions disponibles : {dimensions_nominales()} po."
        )
    if vert and gros_bois and ligne["green_timber"] is not None:
        return ligne["green_timber"]
    if ligne["dry"] is None:
        raise ValueError(
            f"La dimension nominale {nominale} po est offerte seulement pour le gros bois vert "
            "(tableau A.3) : face étroite de 5 po ou plus et bois vert."
        )
    return ligne["green"] if vert else ligne["dry"]


# --- Pièce entrée en texte libre (datum-retours #20) ---

# Façon dont les dimensions entrées sont lues (DimensionsDeLaPiece.lecture)
NOMINALES = "nominales"  # dimensions nominales du tableau A.3 (ex. 2x6 sec -> 38 x 140 mm)
BRUTES = "brutes"  # convention de l'utilisateur, hors tableau A.3 (dimension_nette(brut=True))
REELLES = "réelles"  # entrées en mm : utilisées telles quelles


@dataclass(frozen=True)
class DimensionsDeLaPiece:
    """
    Dimensions nettes d'une pièce entrée en texte libre (datum-retours #20).

    Args:
        nombre_de_plis (int): Nombre de plis (sans symbole dans la norme, 6.5.3.2.4).
        largeur_d_un_pli (float): Largeur nette d'un pli, mm (sans symbole ; b est la largeur totale).
        d (float): Hauteur nette de l'élément, mm (3.2 : « depth of member »).
        vert (bool): Bois vert (teneur en humidité > 19 %).
        lecture (str): NOMINALES, BRUTES ou REELLES.
        gros_bois (bool): Gros bois (est_gros_bois), pour des dimensions nominales seulement.
        piece (PieceEntree): Ce que dit le texte (moteur/commun/piece.py).
    """

    nombre_de_plis: int
    largeur_d_un_pli: float
    d: float
    vert: bool
    lecture: str
    gros_bois: bool
    piece: PieceEntree

    @property
    def b(self) -> float:
        """b = largeur de l'élément, mm : largeur totale, tous les plis compris (3.2, p. 35 ; issue #95)."""
        return self.nombre_de_plis * self.largeur_d_un_pli

    def description(self) -> str:
        """
        Ce que Datum a compris, en mots, sans les dimensions nettes (l'interface les ajoute dans les deux
        unités). Ex. « 2 plis de 2x6, sec, dimensions nominales (tableau A.3) » ;
        « 5 1/4 x 8 7/16 po, sec, dimensions brutes » ; « 89x140 mm, sec, dimensions réelles ».
        """
        p = self.piece
        # « 2x6 » collé ; « 5 1/4 x 8 7/16 » espacé, pour que les fractions restent lisibles
        fractionnaire = any(c in p.texte_largeur + p.texte_hauteur for c in " -/")
        nom = f"{p.texte_largeur}{' x ' if fractionnaire else 'x'}{p.texte_hauteur}"
        if self.lecture != NOMINALES:
            nom += " mm" if p.en_mm else " po"  # « 2x6 » nominal se lit sans unité
        if self.nombre_de_plis > 1:
            nom = f"{self.nombre_de_plis} plis de {nom}"
        etat = "vert" if self.vert else "sec"
        if self.lecture == NOMINALES:
            source = "dimensions nominales (tableau A.3" + (", gros bois vert)" if self.gros_bois and self.vert else ")")
        else:
            source = f"dimensions {self.lecture}"
        return f"{nom}, {etat}, {source}"


def dimensions_de_la_piece(piece: PieceEntree) -> DimensionsDeLaPiece:
    """
    Tableau A.3 Dimensions nettes d'une pièce entrée en texte libre (datum-retours #20).

    Lecture des dimensions (réponses de l'utilisateur, datum-retours #20, 27 novembre 2026) :
        1. en millimètres (« mm ») : dimensions réelles, utilisées telles quelles ;
        2. avec le mot « brut » : dimensions brutes (dimension_nette(brut=True), convention de
           l'utilisateur) ;
        3. sinon, si les deux dimensions sont des dimensions nominales du tableau A.3 pour ce bois (sec ou
           vert ; ex. 7 et 9 po : gros bois vert seulement) : dimensions nominales du tableau A.3 ;
        4. sinon (dimension non entière ou absente du tableau A.3, ex. 5 1/4 x 8 7/16, 2x11, 6x9 sec) :
           dimensions brutes, sans mot-clé. Les deux dimensions de la pièce sont alors brutes, comme
           avec l'ancienne case « Dimensions brutes » (une seule case pour b et d).
    L'interface affiche toujours ce qui a été compris (description()), pour qu'une erreur se voie.

    Args:
        piece (PieceEntree): Texte lu par moteur/commun/piece.lire_piece().

    Returns:
        DimensionsDeLaPiece: Nombre de plis, largeur nette d'un pli (mm), d (mm) et lecture retenue.
    """
    largeur_entree, hauteur_entree = piece.largeur_d_un_pli_entree, piece.hauteur_entree
    commun = dict(nombre_de_plis=piece.nombre_de_plis, vert=piece.vert, piece=piece)

    # 1. Millimètres : dimensions réelles
    if piece.en_mm:
        return DimensionsDeLaPiece(
            largeur_d_un_pli=largeur_entree, d=hauteur_entree, lecture=REELLES, gros_bois=False, **commun
        )

    # 3. Dimensions nominales du tableau A.3, si les deux y sont pour ce bois (sec ou vert)
    if not piece.brut:
        gros_bois = est_gros_bois(largeur_entree, hauteur_entree)
        try:
            # dimension_nette() refuse (ValueError) une dimension absente du tableau A.3 pour ce bois
            largeur = dimension_nette(largeur_entree, vert=piece.vert, gros_bois=gros_bois)
            d = dimension_nette(hauteur_entree, vert=piece.vert, gros_bois=gros_bois)
        except ValueError:
            pass  # 4. absente du tableau A.3 : lue comme brute, plus bas
        else:
            return DimensionsDeLaPiece(
                largeur_d_un_pli=largeur, d=d, lecture=NOMINALES, gros_bois=gros_bois, **commun
            )

    # 2. et 4. Dimensions brutes (convention de l'utilisateur, conservée telle quelle)
    return DimensionsDeLaPiece(
        largeur_d_un_pli=dimension_nette(largeur_entree, vert=piece.vert, brut=True),
        d=dimension_nette(hauteur_entree, vert=piece.vert, brut=True),
        lecture=BRUTES,
        gros_bois=False,
        **commun,
    )
