"""
CSA O86:19 - 5.3 Conditions et coefficients influant sur la résistance (p. 41-44).

    5.3.2 Coefficient de durée d'application de la charge, K_D
        5.3.2.1 Généralités : K_D selon le tableau 5.1, sans dépasser 1,15
        5.3.2.2 Coefficient de durée d'application continue de la charge :
            K_D = 1,0 - 0,50 log(P_L / P_s) >= 0,65, si P_L > P_s
    5.3.8 Réduction de la section transversale (p. 44)
        5.3.8.2 Limite : section nette >= 75 % de la section brute

Points d'interprétation en attente (issue #58) : comportement de l'ancien code conservé.
"""

import math

# Tableau 5.1 (p. 42) : durée d'application de la charge -> K_D
TABLEAU_5_1: dict[str, float] = {
    "courte": 1.15,
    "normale": 1.00,
    "continue": 0.65,
}
K_D_MAXIMAL = 1.15  # 5.3.2.1 : K_D ne doit pas dépasser 1,15
K_D_MINIMAL_CONTINUE = 0.65  # 5.3.2.2 : K_D >= 0,65
SECTION_NETTE_MINIMALE = 0.75  # 5.3.8.2 : section nette >= 75 % de la section brute


def K_D(duree: str) -> float:
    """
    5.3.2.1 Coefficient de durée d'application de la charge, K_D (tableau 5.1).

    Args:
        duree (str): Durée d'application de la charge : « courte », « normale » ou « continue ».

    Returns:
        float: K_D.

    Raises:
        ValueError: Si la durée est inconnue.
    """
    try:
        return min(TABLEAU_5_1[duree], K_D_MAXIMAL)
    except KeyError:
        raise ValueError(f"Durée d'application de la charge invalide : {duree!r} (tableau 5.1).") from None


def P_s(S: float = 0.0, L: float = 0.0) -> float:
    """
    5.3.2.2 Charge spécifiée de durée d'application normale P_s, à partir des charges de neige et des
    surcharges spécifiées (coefficients de risque égaux à 1,0).

    P_s = max(S ; L ; S + 0,5 L ; 0,5 S + L) : la plus grande des quatre combinaisons de 5.3.2.2
    (décision de l'utilisateur, issue #58).

    Args:
        S (float, optional): Charge de neige spécifiée. Default to 0.
        L (float, optional): Surcharge spécifiée (même unité que S). Default to 0.

    Returns:
        float: P_s (même unité que S et L).
    """
    return max(S, L, S + 0.5 * L, 0.5 * S + L)


def K_D_charge_continue(P_L: float, P_s: float) -> float:
    """
    5.3.2.2 Coefficient de durée d'application continue de la charge.

    K_D = 1,0 - 0,50 log(P_L / P_s) >= 0,65, applicable si P_L > P_s.

    Args:
        P_L (float): Charge spécifiée de durée d'application continue (même unité que P_s).
        P_s (float): Charge spécifiée de durée d'application normale (S, L, S + 0,5 L ou 0,5 S + L,
            coefficients de risque égaux à 1,0).

    Returns:
        float: K_D.

    Raises:
        ValueError: Si P_s n'est pas positive, ou si P_L <= P_s (5.3.2.2 ne s'applique pas).
    """
    if P_s <= 0:
        raise ValueError("P_s doit être positive (5.3.2.2).")
    if P_L <= P_s:
        raise ValueError("5.3.2.2 s'applique seulement si P_L > P_s.")
    return min(max(1.0 - 0.50 * math.log10(P_L / P_s), K_D_MINIMAL_CONTINUE), K_D_MAXIMAL)


def verifier_section_nette(A_n: float, A_g: float) -> None:
    """
    5.3.8.2 Limite de la section nette (p. 44).

    « La section nette ne doit en aucun cas être inférieure à 75 % de la section brute. »
    (« The net section shall not be less than 75% of the gross section. »)

    Args:
        A_n (float): Aire de la section transversale nette, mm² (5.3.8.1).
        A_g (float): Aire de la section transversale brute, mm².

    Raises:
        ValueError: Si A_n n'est pas positive, si A_n > A_g, ou si A_n < 0,75 A_g.
    """
    if A_n <= 0:
        raise ValueError("L'aire nette A_n doit être positive (5.3.8.1).")
    if A_n > A_g:
        raise ValueError(
            f"L'aire nette (An = {A_n:g} mm²) ne peut pas dépasser l'aire brute "
            f"(Ag = {A_g:g} mm²) (5.3.8.1)."
        )
    if A_n < SECTION_NETTE_MINIMALE * A_g:
        raise ValueError(
            f"L'aire nette (An = {A_n:g} mm²) ne doit pas être inférieure à 0.75 Ag = "
            f"{SECTION_NETTE_MINIMALE * A_g:g} mm² (5.3.8.2)."
        )
