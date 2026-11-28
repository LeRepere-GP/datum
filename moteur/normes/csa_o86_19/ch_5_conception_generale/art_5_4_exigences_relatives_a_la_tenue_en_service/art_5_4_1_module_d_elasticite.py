"""
CSA O86:19 - 5.4.1 Module d'élasticité (p. 44).

« Le module d'élasticité, dans les calculs de rigidité, E_S, doit être calculé comme suit :
E_S = E (K_SE K_T) »
(« The modulus of elasticity for stiffness calculations, E_S, shall be calculated as follows:
E_S = E (K_SE K_T) »)

Note sur le symbole : la version anglaise de 3.2 définit E_S comme « modulus of elasticity for
stiffness calculations », comme 5.4.1. La version française de 3.2 (p. 35) donne « module d'élasticité
transversal », la même définition que E⊥ ; c'est la définition de 5.4.1 qui est retenue ici (question
posée à l'utilisateur dans la PR).
"""


def E_S(E: float, K_SE: float, K_T: float) -> float:
    """
    5.4.1 Module d'élasticité pour les calculs de rigidité, E_S = E (K_SE K_T).

    Args:
        E (float): Module d'élasticité prévu, MPa (tableaux 6.3 à 6.9).
        K_SE (float): Coefficient de conditions d'utilisation relatif au module d'élasticité
            (tableau 6.10).
        K_T (float): Coefficient de traitement du module d'élasticité (tableau 6.11). C'est le seul
            usage du K_T du module d'élasticité (voir CLAUDE.md, KT dans KC).

    Returns:
        float: E_S, MPa.

    Raises:
        ValueError: Si E, K_SE ou K_T n'est pas positif.
    """
    # Calculs de base en valeurs positives seulement (CLAUDE.md)
    if E <= 0 or K_SE <= 0 or K_T <= 0:
        raise ValueError("E, K_SE et K_T doivent être positifs (5.4.1).")
    return E * (K_SE * K_T)
