"""
CSA O86:19 - 5.4.4 Accumulation d'eau (p. 45).

« Les systèmes d'ossature des toits doivent faire l'objet d'une analyse rationnelle afin d'assurer la
tenue en service en cas d'accumulation d'eau, à moins que :
a) la surface du toit ne soit inclinée de manière à permettre l'écoulement libre de l'eau de pluie et
   empêcher son accumulation; ou
b) dans le cas d'un système à appuis simples sollicité par une charge uniformément répartie, la
   condition suivante soit satisfaite : ΣΔ / w < 65
où
ΣΔ = somme des flèches dues à cette charge, en mm, pour tous les éléments constitutifs du système
     (platelage, poutres secondaires, poutres principales, etc.)
w  = charge totale spécifiée uniformément répartie, kN/m² »

Δ et w sont des symboles définis dans l'article (pas à 3.2). Le cas a) (pente) est une constatation de
l'ingénieur, sans calcul : seul le cas b) est codé.
"""

LIMITE = 65  # 5.4.4 b) : ΣΔ / w < 65 (mm, kN/m²) ; inégalité stricte


def somme_Delta_sur_w(Delta: list[float], w: float) -> float:
    """
    5.4.4 b) Rapport ΣΔ / w.

    Args:
        Delta (list[float]): Flèche Δ de chaque élément constitutif du système (platelage, poutres
            secondaires, poutres principales, etc.) due à la charge w, mm.
        w (float): Charge totale spécifiée uniformément répartie, kN/m².

    Returns:
        float: ΣΔ / w, mm / (kN/m²).

    Raises:
        ValueError: Si w n'est pas positive, si la liste est vide ou si une flèche est négative.
    """
    if w <= 0:
        raise ValueError("La charge w doit être positive (5.4.4).")
    if not Delta:
        raise ValueError("Entrer la flèche d'au moins un élément du système (5.4.4).")
    # Calculs de base en valeurs positives seulement (CLAUDE.md)
    if any(fleche < 0 for fleche in Delta):
        raise ValueError("Les flèches Δ doivent être positives ou nulles (5.4.4).")
    return sum(Delta) / w


def accumulation_d_eau_sans_analyse_rationnelle(Delta: list[float], w: float) -> bool:
    """
    5.4.4 b) Condition ΣΔ / w < 65 d'un système à appuis simples sous une charge uniformément répartie.

    Si elle est satisfaite, l'analyse rationnelle de l'accumulation d'eau n'est pas exigée. À
    ΣΔ / w = 65 exactement, la condition n'est pas satisfaite (inégalité stricte de la norme).

    Args:
        Delta (list[float]): Flèche Δ de chaque élément constitutif du système, mm.
        w (float): Charge totale spécifiée uniformément répartie, kN/m².

    Returns:
        bool: True si ΣΔ / w < 65 (pas d'analyse rationnelle exigée par 5.4.4 b)).
    """
    return somme_Delta_sur_w(Delta, w) < LIMITE
