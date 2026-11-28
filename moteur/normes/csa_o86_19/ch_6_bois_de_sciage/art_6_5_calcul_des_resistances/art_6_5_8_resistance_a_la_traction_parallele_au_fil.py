"""
CSA O86:19 - 6.5.8 Résistance à la traction parallèle au fil (p. 74).

    T_r = phi F_t A_n K_Zt, phi = 0,9
    F_t = f_t (K_D K_H K_St K_T)

A_n : aire de la section transversale nette (5.3.8, p. 44) ; elle ne doit en aucun cas être inférieure
à 75 % de la section brute (5.3.8.2).

Réduction de la section (décision de l'utilisateur, PR #107) : par défaut, aucune réduction (A_n = A_g).
Sinon, l'utilisateur indique ce qui est retiré de b, de d ou des deux, et A_n est calculée avec la
section résiduelle : A_n = (b - réduction de b) (d - réduction de d) (confirmé dans la PR #107 : un 2x6
de 1.5 po x 5.5 po dont on retire 0.5 po de b et 0.5 po de d donne une section de 1 po x 5 po). Ces réductions n'ont pas de symbole dans
la norme.
"""

from moteur.commun.nombres import cs
from moteur.commun.registre import enregistrer
from moteur.commun.resultat import Donnee, Etape, Resultat
from moteur.normes.csa_o86_19 import NORME
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_1_calculs_aux_etats_limites import (
    verifier_etat_limite_ultime,
)
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_3_conditions_et_coefficients_influant_sur_la_resistance import (  # noqa: E501
    verifier_section_nette,
)

EDITION = "csa_o86_19"
PHI = 0.9  # 6.5.8


# FONCTIONS SIMPLES (dans l'ordre de la norme)
def F_t(f_t: float, K_D: float = 1, K_H: float = 1, K_St: float = 1, K_T: float = 1) -> float:
    """
    6.5.8 Résistance corrigée en traction parallèle au fil, F_t.

    F_t = f_t (K_D K_H K_St K_T)

    Args:
        f_t (float): Résistance prévue en traction parallèle au fil, MPa (tableaux 6.4 à 6.9).
        K_D, K_H, K_St, K_T (float, optional): Coefficients de correction. Default to 1.

    Returns:
        float: F_t, MPa.
    """
    return f_t * (K_D * K_H * K_St * K_T)


def T_r(F_t: float, A_n: float, K_Zt: float = 1) -> float:
    """
    6.5.8 Résistance pondérée à la traction parallèle au fil, T_r.

    T_r = phi F_t A_n K_Zt, phi = 0,9

    Args:
        F_t (float): Résistance corrigée en traction parallèle au fil, MPa.
        A_n (float): Aire de la section transversale nette, mm² (5.3.8).
        K_Zt (float, optional): Coefficient de dimensions en traction (6.4.5, tableau 6.13).
            Default to 1.

    Returns:
        float: T_r, N.
    """
    return PHI * F_t * A_n * K_Zt


# VÉRIFICATIONS
@enregistrer(EDITION, "6.5.8", "Résistance à la traction parallèle au fil")
def verifier_traction(
    b: float,
    d: float,
    f_t: float,
    plis: int = 1,
    reduction_de_b: float = 0,
    reduction_de_d: float = 0,
    K_D: float = 1,
    K_H: float = 1,
    K_St: float = 1,
    K_T: float = 1,
    K_Zt: float = 1,
    T_f: float | None = None,
    source_resistances: str = "Tableaux 6.4 à 6.9",
    source_K_D: str = "Tableau 5.1",
) -> Resultat:
    """
    6.5.8 Résistance pondérée à la traction parallèle au fil d'un élément en bois de sciage.

    Args:
        b (float): Largeur de l'élément, mm (3.2) : largeur totale d'un élément composé, tous les plis
            compris (issue #95).
        d (float): Hauteur de l'élément, mm.
        f_t (float): Résistance prévue en traction parallèle au fil, MPa.
        plis (int, optional): Nombre de plis. Default to 1.
        reduction_de_b, reduction_de_d (float, optional): Partie de la largeur b et de la hauteur d
            retirée de la section (5.3.8.1 : matériau enlevé par perçage, rainurage, entaillage,
            etc.), mm. Pas de symbole dans la norme. Default to 0 : aucune réduction, A_n = A_g.
        K_D, K_H, K_St, K_T, K_Zt (float, optional): Coefficients de correction. Default to 1.
        T_f (float | None, optional): Charge de traction axiale pondérée, kN. Default to None.
        source_resistances (str, optional): Tableau des résistances prévues (6.3), pour la note de
            calcul (voir art_6_3.tableau_des_resistances()). Default to "Tableaux 6.4 à 6.9".
        source_K_D (str, optional): Source de K_D pour la note de calcul : « Tableau 5.1 », ou
            « 5.3.2.2 » si K_D est calculé à partir des charges. Default to "Tableau 5.1".

    Returns:
        Resultat: Trace du calcul. T_r en N ; vérification en kN.

    Raises:
        ValueError: Si une réduction est négative, si elle retire toute la largeur b ou toute la
            hauteur d, ou si A_n n'est pas positive ou est inférieure à 0,75 A_g (5.3.8.2).
    """
    r = Resultat(NORME, "6.5.8", "Résistance à la traction parallèle au fil", "traction")
    for donnee in (
        Donnee("b", "Largeur de l'élément", b, "mm", "dimension"),
        Donnee("d", "Hauteur de l'élément", d, "mm", "dimension"),
        Donnee("", "Nombre de plis", plis),  # pas de symbole dans la norme
        # Largeur d'un pli : « élément individuel » (6.5.3.2.4), sans symbole dans la norme
        *([Donnee("", "Largeur d'un pli", b / plis, "mm", "dimension")] if plis > 1 else []),
        Donnee("f_t", "Résistance prévue en traction parallèle au fil", f_t, "MPa", "contrainte",
               source_resistances),
        Donnee("K_D", "Coefficient de durée d'application de la charge", K_D, source=source_K_D),
        Donnee("K_H", "Coefficient de système", K_H, source="Tableau 6.12"),
        Donnee("K_{St}", "Coefficient de conditions d'utilisation (traction parallèle au fil)", K_St,
               source="Tableau 6.10"),
        Donnee("K_T", "Coefficient de traitement", K_T, source="Tableau 6.11"),
        Donnee("K_{Zt}", "Coefficient de dimensions (traction)", K_Zt, source="Tableau 6.13"),
    ):
        r.ajouter_donnee(donnee)

    f_t_corrige = r.ajouter_etape(Etape(
        "6.5.8", "Résistance corrigée en traction parallèle au fil", "F_t",
        r"F_t = f_t \, (K_D \, K_H \, K_{St} \, K_T)",
        rf"{cs(f_t)} \times ({cs(K_D)} \times {cs(K_H)} \times {cs(K_St)} \times {cs(K_T)})",
        F_t(f_t, K_D, K_H, K_St, K_T), "MPa", "contrainte",
    ))
    a_g = r.ajouter_etape(Etape(
        "5.3.8.1", "Aire de la section transversale brute", "A_g",
        r"A_g = b \, d", rf"{cs(b)} \times {cs(d)}", b * d, "mm²", "aire",  # aire : affichée aussi en po²
    ))
    if reduction_de_b < 0 or reduction_de_d < 0:
        raise ValueError("Une réduction de la section ne peut pas être négative (5.3.8.1).")
    # Une réduction qui retire toute la largeur b ou toute la hauteur d (ou plus) ne laisse aucune
    # section. Ce contrôle est nécessaire : si les deux réductions dépassent b et d, les deux facteurs
    # de (b - réduction de b) (d - réduction de d) sont négatifs et leur produit serait positif (ex.
    # 2x6 de 38 mm x 140 mm, 76 mm retirés de b et 280 mm de d : (-38 mm) x (-140 mm) = 5320 mm²).
    if reduction_de_b >= b or reduction_de_d >= d:
        raise ValueError(
            f"La réduction ne peut pas retirer toute la section : réduction de b < b = {b:g} mm et "
            f"réduction de d < d = {d:g} mm (5.3.8.1)."
        )
    if reduction_de_b == 0 and reduction_de_d == 0:
        a_n = r.ajouter_etape(Etape(
            "5.3.8.1", "Aire de la section transversale nette (aucune réduction)", "A_n",
            r"A_n = A_g", rf"{cs(a_g)}", a_g, "mm²", "aire",  # aire : affichée aussi en po²
        ))
    else:
        r.ajouter_donnee(Donnee("", "Réduction de la largeur b", reduction_de_b, "mm", "dimension"))
        r.ajouter_donnee(Donnee("", "Réduction de la hauteur d", reduction_de_d, "mm", "dimension"))
        A_n = (b - reduction_de_b) * (d - reduction_de_d)
        verifier_section_nette(A_n, a_g)
        a_n = r.ajouter_etape(Etape(
            "5.3.8.1", "Aire de la section transversale nette", "A_n",
            r"A_n = (b - \text{réduction de } b) \, (d - \text{réduction de } d)",
            rf"({cs(b)} - {cs(reduction_de_b)}) \times ({cs(d)} - {cs(reduction_de_d)})",
            A_n, "mm²", "aire",  # aire : affichée aussi en po²
        ))
        # Rapport sans symbole dans la norme (5.3.8.2 : au moins 75 % de la section brute)
        r.ajouter_etape(Etape(
            "5.3.8.2", "Section nette par rapport à la section brute (au moins 0.75)", "",
            r"\frac{A_n}{A_g} \geq 0.75", rf"\frac{{{cs(a_n)}}}{{{cs(a_g)}}}", a_n / a_g,
        ))
    t_r = r.ajouter_etape(Etape(
        "6.5.8", "Résistance pondérée à la traction parallèle au fil", "T_r",
        r"T_r = \phi \, F_t \, A_n \, K_{Zt}",
        rf"0.9 \times {cs(f_t_corrige)} \times {cs(a_n)} \times {cs(K_Zt)}",
        T_r(f_t_corrige, a_n, K_Zt), "N",
    ))

    if T_f is not None:
        r.verification = verifier_etat_limite_ultime(T_f, t_r / 1000, "T_f", "T_r", "kN", "force")

    return r
