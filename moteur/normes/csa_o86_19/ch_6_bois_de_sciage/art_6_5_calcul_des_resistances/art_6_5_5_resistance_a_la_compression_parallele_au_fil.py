"""
CSA O86:19 - 6.5.5 Résistance à la compression parallèle au fil (p. 68-71).

    6.5.5.1 Longueur effective, L_e
    6.5.5.2.1 Généralités : P_r vérifiée pour les deux axes
    6.5.5.2.2 Élancement, C_C
    6.5.5.2.4 Résistance pondérée à la compression sous charge axiale (P_r, F_c, K_Zc)
    6.5.5.2.5 Coefficient d'élancement, K_C
    6.5.5.4 Éléments composés en compression (p. 70-71) : 2 à 5 plis cloués, boulonnés ou assemblés
        par anneaux fendus (issue #32)

Interprétations validées avec l'utilisateur (CLAUDE.md) :
    - K_Zc : L = longueur de l'élément (pas L_e ni la longueur entre appuis latéraux).
    - K_T dans K_C : K_T des « autres propriétés » (tableau 6.11), le même que dans F_c.
    - L_e = K_e L (6.5.5.1), avec L = entraxe des appuis latéraux dans le plan de flambage (note du
      tableau A.4). K_e est entré en chiffre ; le tableau A.4 (annexe A, informative) le donne selon
      les conditions d'appui (art_A_6_5_5_1_coefficient_de_longueur_effective.py).

Décisions de l'utilisateur pour 6.5.5.4 (issue #32, commentaire du 27 novembre 2026) :
    - 6.5.5.4.6 (p. 71) « Les coefficients de réduction [...] peuvent être omis pour le flambage dans
      la direction de l'axe principal des pièces » (anglais, p. 66 : « may be omitted for buckling in
      the direction of the strong axis of the laminations ») : l'axe principal des pièces est le
      flambage selon d. Le coefficient de réduction (0,60, 0,75 ou 0,80) s'applique donc seulement
      au flambage selon b, et il est omis selon d, toujours (pas de case à cocher).
    - Datum ne vérifie pas l'assemblage (espacements, pénétration, rangées, chapitre 12) :
      l'ingénieur choisit le type d'assemblage et les exigences de la norme sont affichées en notes.
    - Hors de 6.5.5.4.1 (plus de 5 plis, ou pièces de moins de 38 mm) : calcul refusé, sans P_r.
    - K_H = 1,00 : un élément de 2 plis ou plus prend toujours la colonne « Poutres composées » du
      tableau 6.12 (décision #7) ; en compression parallèle au fil, cette colonne donne 1,00 (p. 62).
      K_H est reçu en paramètre ; l'interface le prend de art_6_4.K_H().
    - b = largeur de l'élément, tous les plis compris (3.2, décision #95). La largeur d'un pli et le
      nombre de plis n'ont pas de symbole dans la norme.
    - 6.5.5.4.1 (PR #114) : P_r(b) = la valeur la plus permissive entre l'élément composé réduit (60, 75
      ou 80 %) et la somme des plis calculés seuls. Si un pli seul a C_C > 50 (6.5.5.2.2), seule la
      valeur de l'élément composé (C_C le plus petit) est possible.
"""

from moteur.commun.nombres import cs
from moteur.commun.unites import deux_unites
from moteur.commun.registre import enregistrer
from moteur.commun.resultat import Donnee, Etape, Resultat
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_1_calculs_aux_etats_limites import (
    verifier_etat_limite_ultime,
)
from moteur.normes.csa_o86_19 import NORME

EDITION = "csa_o86_19"


# FONCTIONS SIMPLES (dans l'ordre de la norme)
def L_e(K_e: float, L: float) -> float:
    """
    6.5.5.1 Longueur effective, L_e.

    L_e = K_e L

    Args:
        K_e (float): Coefficient de longueur effective (valeurs recommandées : tableau A.4).
        L (float): Entraxe des appuis latéraux de l'élément dans le plan de flambage considéré, mm
            (note du tableau A.4).

    Returns:
        float: L_e, mm.

    Raises:
        ValueError: Si une valeur n'est pas positive.
    """
    if K_e <= 0 or L <= 0:
        raise ValueError("K_e et la longueur entre les appuis latéraux doivent être positifs (6.5.5.1).")

    return K_e * L


def C_C(L_e: float, dimension: float) -> float:
    """
    6.5.5.2.2 Élancement, C_C.

    C_C = longueur effective associée à la dimension / dimension, <= 50, selon les deux axes.

    Args:
        L_e (float): Longueur effective associée à la dimension, mm.
        dimension (float): Largeur b ou hauteur d de l'élément (direction du flambage), mm.

    Returns:
        float: C_C.

    Raises:
        ValueError: Si une valeur n'est pas positive ou si C_C > 50.
    """
    if L_e <= 0 or dimension <= 0:
        raise ValueError("La longueur effective et la dimension doivent être positives (6.5.5.2.2).")

    c_c = L_e / dimension
    if c_c > 50:
        raise ValueError(f"L'élancement (Cc = {c_c:.2f}) ne doit pas dépasser 50 (6.5.5.2.2).")

    return c_c


def P_r(F_c: float, A: float, K_Zc: float, K_C: float) -> float:
    """
    6.5.5.2.4 Résistance pondérée à la compression sous charge axiale, P_r.

    P_r = phi F_c A K_Zc K_C, phi = 0,8

    Args:
        F_c (float): F_c = f_c (K_D K_H K_Sc K_T), MPa.
        A (float): Aire de la section transversale, mm².
        K_Zc (float): Coefficient de dimensions en compression.
        K_C (float): Coefficient d'élancement.

    Returns:
        float: P_r, N.
    """
    phi = 0.8
    return phi * F_c * A * K_Zc * K_C


def F_c(f_c: float, K_D: float = 1, K_H: float = 1, K_Sc: float = 1, K_T: float = 1) -> float:
    """
    6.5.5.2.4 Résistance corrigée en compression parallèle au fil, F_c.

    F_c = f_c (K_D K_H K_Sc K_T)

    Args:
        f_c (float): Résistance prévue en compression parallèle au fil, MPa (tableaux 6.4 à 6.9).
        K_D (float, optional): Coefficient de durée d'application de la charge. Default to 1.
        K_H (float, optional): Coefficient de système. Default to 1.
        K_Sc (float, optional): Coefficient de conditions d'utilisation (compression parallèle).
            Default to 1.
        K_T (float, optional): Coefficient de traitement (« autres propriétés »). Default to 1.

    Returns:
        float: F_c, MPa.
    """
    return f_c * (K_D * K_H * K_Sc * K_T)


def K_Zc(d: float, L: float) -> float:
    """
    6.5.5.2.4 Coefficient de dimensions en compression, K_Zc.

    K_Zc = 6,3 (d L)^-0,13 <= 1,3

    Args:
        d (float): Dimension dans la direction du flambage (grande face ou face étroite), mm.
        L (float): Longueur de l'élément, mm (et non la longueur effective ; voir A.6.5.5.2.4 b)).

    Returns:
        float: K_Zc.

    Raises:
        ValueError: Si une valeur n'est pas positive.
    """
    if d <= 0 or L <= 0:
        raise ValueError("La dimension et la longueur doivent être positives (6.5.5.2.4).")

    return min(6.3 * (d * L) ** -0.13, 1.3)


def K_C(
    F_c: float, K_Zc: float, C_C: float, E_05: float, K_SE: float = 1, K_T: float = 1
) -> float:
    """
    6.5.5.2.5 Coefficient d'élancement, K_C.

    K_C = [1,0 + (F_c K_Zc C_C^3) / (35 E_05 K_SE K_T)]^-1

    Args:
        F_c (float): F_c = f_c (K_D K_H K_Sc K_T), MPa.
        K_Zc (float): Coefficient de dimensions en compression.
        C_C (float): Élancement selon l'axe considéré.
        E_05 (float): Module d'élasticité pour les calculs des éléments en compression, MPa
            (0,82E pour le MSR, 0,75E pour le MEL, tableaux 6.4 à 6.7 pour le bois classé
            visuellement).
        K_SE (float, optional): Coefficient de conditions d'utilisation relatif au module
            d'élasticité. Default to 1.
        K_T (float, optional): Coefficient de traitement des « autres propriétés », le même que
            dans F_c. Default to 1.

    Returns:
        float: K_C.
    """
    return (1 + (F_c * K_Zc * C_C**3) / (35 * E_05 * K_SE * K_T)) ** -1


# 6.5.5.4 ÉLÉMENTS COMPOSÉS EN COMPRESSION (p. 70-71)
# Types d'assemblage de 6.5.5.4.1 : « clous, [...] boulons ou [...] anneaux fendus utilisés avec des
# boulons ». Les identifiants servent dans le code et l'interface ; le texte va dans la note.
CLOUS = "clous"
BOULONS = "boulons"
ANNEAUX_FENDUS = "anneaux_fendus"
# Type d'assemblage : (article, description pour la note, coefficient de réduction)
ASSEMBLAGES = {
    CLOUS: ("6.5.5.4.2", "Clous ou pointes", 0.60),  # « égale à 60 % » (6.5.5.4.2, p. 70)
    BOULONS: ("6.5.5.4.3", "Boulons", 0.75),  # « égale à 75 % » (6.5.5.4.3, p. 70)
    ANNEAUX_FENDUS: ("6.5.5.4.4", "Anneaux fendus et boulons", 0.80),  # « égale à 80 % » (6.5.5.4.4)
}
# 6.5.5.4.1 : « deux à cinq éléments individuels d'au moins 38 mm d'épaisseur »
NOMBRE_DE_PLIS_MINIMAL = 2
NOMBRE_DE_PLIS_MAXIMAL = 5
EPAISSEUR_MINIMALE_D_UN_PLI = 38  # mm


def _verifier_assemblage(assemblage: str) -> None:
    """Lève une erreur si le type d'assemblage n'est pas un de ceux de 6.5.5.4.2 à 6.5.5.4.4."""
    if assemblage not in ASSEMBLAGES:
        raise ValueError(
            f"Type d'assemblage inconnu : {assemblage!r}. Choix : {sorted(ASSEMBLAGES)} (6.5.5.4.1)."
        )


def verifier_les_plis(nombre_de_plis: int, largeur_d_un_pli: float) -> None:
    """
    6.5.5.4.1 Généralités : nombre et épaisseur des pièces d'un élément composé en compression.

    « Les éléments rectangulaires composés en compression doivent être constitués de deux à cinq
    éléments individuels d'au moins 38 mm d'épaisseur » (p. 70). Les plis sont côte à côte selon b :
    l'épaisseur d'un pli est donc sa largeur (b d'un pli).

    Décision de l'utilisateur (issue #32) : hors de ces limites, le calcul est refusé (pas de P_r).

    Args:
        nombre_de_plis (int): Nombre de plis (éléments individuels), sans symbole dans la norme.
        largeur_d_un_pli (float): Épaisseur d'un pli (sa largeur, dans la direction de b), mm.

    Raises:
        ValueError: S'il y a moins de 2 ou plus de 5 plis, ou si un pli a moins de 38 mm.
    """
    if not NOMBRE_DE_PLIS_MINIMAL <= nombre_de_plis <= NOMBRE_DE_PLIS_MAXIMAL:
        raise ValueError(
            f"Un élément composé en compression doit avoir de 2 à 5 plis (6.5.5.4.1) : "
            f"{nombre_de_plis} plis. Calcul refusé."
        )
    if largeur_d_un_pli < EPAISSEUR_MINIMALE_D_UN_PLI:
        raise ValueError(
            f"Les plis d'un élément composé en compression doivent avoir au moins 38 mm d'épaisseur "
            f"(6.5.5.4.1) : {largeur_d_un_pli:g} mm. Calcul refusé."
        )


def coefficient_de_reduction(assemblage: str) -> float:
    """
    6.5.5.4.2 à 6.5.5.4.4 Coefficient de réduction de la résistance d'un élément composé.

    Part de la résistance « d'un élément massif de section [brute] équivalente calculée suivant
    l'article 6.5.5.2 » : clous ou pointes 60 % (6.5.5.4.2), boulons 75 % (6.5.5.4.3), anneaux fendus
    et boulons 80 % (6.5.5.4.4). Pas de symbole dans la norme.

    Args:
        assemblage (str): CLOUS, BOULONS ou ANNEAUX_FENDUS.

    Returns:
        float: 0,60, 0,75 ou 0,80 (sans unité).

    Raises:
        ValueError: Si le type d'assemblage est inconnu.
    """
    _verifier_assemblage(assemblage)
    return ASSEMBLAGES[assemblage][2]


def resistance_reduite(coefficient: float, resistance_de_l_element_massif: float) -> float:
    """
    6.5.5.4.2 à 6.5.5.4.4 Résistance de l'élément composé : coefficient x résistance de l'élément
    massif de section équivalente (6.5.5.2). Pas de symbole dans la norme.

    Args:
        coefficient (float): Coefficient de réduction (coefficient_de_reduction()).
        resistance_de_l_element_massif (float): P_r de l'élément massif équivalent (6.5.5.2.4), N.

    Returns:
        float: Résistance réduite, N.
    """
    return coefficient * resistance_de_l_element_massif


def resistance_combinee_des_pieces_individuelles(nombre_de_plis: int, resistance_d_un_pli: float) -> float:
    """
    6.5.5.4.1 et 6.5.5.4.5 « Résistance pondérée combinée des pièces individuelles considérées comme
    des éléments individuels » : somme des P_r des plis. Les plis d'un élément de Datum sont tous
    identiques : la somme est nombre de plis x P_r d'un pli. Pas de symbole dans la norme.

    Args:
        nombre_de_plis (int): Nombre de plis.
        resistance_d_un_pli (float): P_r d'un pli considéré comme un élément simple (6.5.5.2.4), N.

    Returns:
        float: Résistance combinée des plis, N.
    """
    return nombre_de_plis * resistance_d_un_pli


def P_r_element_compose(resistance_reduite: float, resistance_combinee: float | None) -> float:
    """
    6.5.5.4.1 Résistance pondérée à la compression de l'élément composé, P_r.

    « [...] peut être la plus grande des valeurs calculées suivant l'article 6.5.5.4.2, 6.5.5.4.3 ou
    6.5.5.4.4, ou comme la résistance pondérée combinée des pièces individuelles considérées comme
    des éléments individuels » (p. 70).

    Args:
        resistance_reduite (float): Résistance de 6.5.5.4.2, 6.5.5.4.3 ou 6.5.5.4.4, N.
        resistance_combinee (float | None): Résistance combinée des pièces individuelles, N. None si
            elle ne peut pas être calculée (ex. C_C d'un pli > 50, 6.5.5.2.2).

    Returns:
        float: P_r, N.
    """
    if resistance_combinee is None:
        return resistance_reduite
    return max(resistance_reduite, resistance_combinee)


def exigences_de_l_assemblage(assemblage: str, largeur_d_un_pli: float, d: float) -> list[str]:
    """
    Exigences de 6.5.5.4.1 à 6.5.5.4.4 pour le type d'assemblage choisi, en notes.

    Décision de l'utilisateur (issue #32) : Datum ne vérifie pas l'assemblage. Il affiche les exigences
    de la norme (page et note PDF) ; l'ingénieur s'assure qu'elles sont respectées. Les valeurs limites
    qui ne dépendent que de la section sont calculées pour aider (ex. 6 x l'épaisseur du pli le plus
    mince). Tous les plis ont la même épaisseur ici : la pièce la plus mince est un pli.

    Args:
        assemblage (str): CLOUS, BOULONS ou ANNEAUX_FENDUS.
        largeur_d_un_pli (float): Épaisseur d'un pli (dans la direction de b), mm.
        d (float): Largeur des pièces (hauteur de l'élément, d), mm.

    Returns:
        list[str]: Une note par exigence, dans l'ordre de la norme.

    Raises:
        ValueError: Si le type d'assemblage est inconnu.
    """
    _verifier_assemblage(assemblage)
    # 6 x l'épaisseur de la pièce la plus mince : limite d'espacement longitudinal (6.5.5.4.2 a),
    # 6.5.5.4.3 a) et 6.5.5.4.4)
    espacement_longitudinal_maximal = 6 * largeur_d_un_pli  # mm
    six_fois = (
        f"6 x {deux_unites(largeur_d_un_pli, 'dimension')} = "
        f"{deux_unites(espacement_longitudinal_maximal, 'dimension')}"
    )
    # 6.5.5.4.2 c) et 6.5.5.4.3 b) : « si les pièces individuelles [...] ont une largeur supérieure à
    # trois fois leur épaisseur, il doit y avoir au moins deux rangées ». Largeur d'une pièce = d ;
    # épaisseur = largeur du pli (direction de b).
    trois_fois = 3 * largeur_d_un_pli  # mm
    if d > trois_fois:
        rangees = (
            f"d = {deux_unites(d, 'dimension')} > 3 x {deux_unites(largeur_d_un_pli, 'dimension')} = "
            f"{deux_unites(trois_fois, 'dimension')} : au moins deux rangées sont requises"
        )
    else:
        rangees = (
            f"d = {deux_unites(d, 'dimension')} <= 3 x {deux_unites(largeur_d_un_pli, 'dimension')} = "
            f"{deux_unites(trois_fois, 'dimension')} : pas exigé pour cette section"
        )

    notes = [
        "Datum ne vérifie pas l'assemblage des plis : l'ingénieur doit s'assurer que les exigences "
        "suivantes sont respectées.",
        "6.5.5.4.1 : distances d'extrémité, de rive et espacements minimaux des attaches conformes à "
        "l'article 12 ; distance d'extrémité maximale d'au plus 1.2 fois la valeur minimale.",
    ]
    if assemblage == CLOUS:
        notes += [
            f"6.5.5.4.2 a) : espacement des clous selon l'axe longitudinal de l'élément d'au plus 6 fois "
            f"l'épaisseur de la pièce la plus mince ({six_fois}) ; espacement perpendiculaire à l'axe "
            "longitudinal d'au plus 20 fois le diamètre des clous.",
            "6.5.5.4.2 b) : les clous pénètrent au moins les trois quarts de l'épaisseur de la dernière "
            "pièce et sont plantés en alternance sur une face et sur l'autre, dans le sens de la longueur.",
            f"6.5.5.4.2 c) : au moins deux rangées de clous sur la largeur si la largeur des pièces "
            f"dépasse 3 fois leur épaisseur ({rangees}).",
        ]
    elif assemblage == BOULONS:
        notes += [
            "6.5.5.4.3 : boulons d'au moins 6 mm (1/4 po) de diamètre.",
            f"6.5.5.4.3 a) : espacement des boulons selon l'axe longitudinal de l'élément d'au plus 6 "
            f"fois l'épaisseur de la pièce la plus mince ({six_fois}) ; espacement perpendiculaire à "
            "l'axe longitudinal d'au plus 10 fois le diamètre des boulons.",
            f"6.5.5.4.3 b) : au moins deux rangées de boulons sur la largeur si la largeur des pièces "
            f"dépasse 3 fois leur épaisseur ({rangees}).",
        ]
    else:  # ANNEAUX_FENDUS
        notes += [
            "6.5.5.4.4 : boulons d'au moins 12 mm (1/2 po) de diamètre et anneaux fendus de 63 mm "
            f"(2 1/2 po), placés à intervalles d'au plus 6 fois l'épaisseur de la pièce la plus mince "
            f"({six_fois}).",
        ]
    return notes


# VÉRIFICATIONS
@enregistrer(EDITION, "6.5.5", "Résistance à la compression parallèle au fil")
def verifier_compression_parallele_au_fil(
    b: float,
    d: float,
    L: float,
    L_selon_b: float,
    L_selon_d: float,
    f_c: float,
    E_05: float,
    K_e_selon_b: float = 1,
    K_e_selon_d: float = 1,
    K_D: float = 1,
    K_H: float = 1,
    K_Sc: float = 1,
    K_T: float = 1,
    K_SE: float = 1,
    P_f: float | None = None,
    source_resistances: str = "Tableaux 6.4 à 6.9",
    source_K_D: str = "Tableau 5.1",
    source_K_e_selon_b: str = "Tableau A.4",
    source_K_e_selon_d: str = "Tableau A.4",
) -> Resultat:
    """
    6.5.5.2 Résistance pondérée à la compression parallèle au fil d'un élément simple, selon les
    deux axes (6.5.5.2.1).

    Args:
        b (float): Largeur de l'élément, mm.
        d (float): Hauteur de l'élément, mm.
        L (float): Longueur de l'élément, mm (pour K_Zc).
        L_selon_b (float): L de 6.5.5.1 pour le flambage selon b : entraxe des appuis latéraux dans ce
            plan de flambage (note du tableau A.4), mm. Symbole affiché : L_(b).
        L_selon_d (float): L de 6.5.5.1 pour le flambage selon d, mm. Symbole affiché : L_(d).
        f_c (float): Résistance prévue en compression parallèle au fil, MPa.
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa.
        K_e_selon_b, K_e_selon_d (float, optional): K_e de 6.5.5.1 pour le flambage selon b et selon
            d (valeurs du tableau A.4). Symboles affichés : K_e(b), K_e(d). Default to 1.
        K_D, K_H, K_Sc, K_T, K_SE (float, optional): Coefficients de correction. Default to 1.
        P_f (float | None, optional): Charge de compression axiale pondérée, kN. Default to None.
        source_resistances (str, optional): Tableau des résistances prévues (6.3), pour la note de
            calcul (voir art_6_3.tableau_des_resistances()). Default to "Tableaux 6.4 à 6.9".
        source_K_D (str, optional): Source de K_D pour la note de calcul : « Tableau 5.1 », ou
            « 5.3.2.2 » si K_D est calculé à partir des charges. Default to "Tableau 5.1".
        source_K_e_selon_b, source_K_e_selon_d (str, optional): Source de K_e(b) et de K_e(d) pour la
            note de calcul : « Tableau A.4 », ou « Entré par l'utilisateur » (issue #90). Default to
            "Tableau A.4".

    Returns:
        Resultat: Trace du calcul. P_r de chaque axe en N ; vérification en kN.

    Raises:
        ValueError: Si une valeur est invalide ou si C_C > 50.
    """
    r = Resultat(NORME, "6.5.5", "Résistance à la compression parallèle au fil", "colonne")
    for donnee in (
        Donnee("b", "Largeur de l'élément", b, "mm", "dimension"),
        Donnee("d", "Hauteur de l'élément", d, "mm", "dimension"),
        Donnee("L", "Longueur de l'élément", L, "mm", "longueur"),
        Donnee("L_{(b)}", "Entraxe des appuis latéraux, flambage selon b", L_selon_b, "mm",
               "longueur"),
        Donnee("L_{(d)}", "Entraxe des appuis latéraux, flambage selon d", L_selon_d, "mm",
               "longueur"),
        Donnee("K_{e(b)}", "Coefficient de longueur effective", K_e_selon_b, source=source_K_e_selon_b),
        Donnee("K_{e(d)}", "Coefficient de longueur effective", K_e_selon_d, source=source_K_e_selon_d),
        Donnee("f_c", "Résistance prévue en compression parallèle au fil", f_c, "MPa", "contrainte",
               source_resistances),
        Donnee("E_{05}", "Module d'élasticité pour les éléments en compression", E_05, "MPa",
               "contrainte", source_resistances),
        Donnee("K_D", "Coefficient de durée d'application de la charge", K_D, source=source_K_D),
        Donnee("K_H", "Coefficient de système", K_H, source="Tableau 6.12"),
        Donnee("K_{Sc}", "Coefficient de conditions d'utilisation (compression)", K_Sc,
               source="Tableau 6.10"),
        Donnee("K_T", "Coefficient de traitement", K_T, source="Tableau 6.11"),
        Donnee("K_{SE}", "Coefficient de conditions d'utilisation (module d'élasticité)", K_SE,
               source="Tableau 6.10"),
    ):
        r.ajouter_donnee(donnee)

    f_c_corrige = r.ajouter_etape(Etape(
        "6.5.5.2.4", "Résistance corrigée en compression parallèle au fil", "F_c",
        r"F_c = f_c \, (K_D \, K_H \, K_{Sc} \, K_T)",
        rf"{cs(f_c)} \times ({cs(K_D)} \times {cs(K_H)} \times {cs(K_Sc)} \times {cs(K_T)})",
        F_c(f_c, K_D, K_H, K_Sc, K_T), "MPa", "contrainte",
    ))
    A = b * d

    resistances = []
    # Symboles de la norme ; l'axe de flambage est entre parenthèses (ex. L_e(b)), sans réutiliser
    # un symbole réservé (L_b est la longueur d'appui, 6.5.6)
    for axe, dimension, K_e, L_appuis in (
        ("b", b, K_e_selon_b, L_selon_b), ("d", d, K_e_selon_d, L_selon_d)
    ):
        l_e = r.ajouter_etape(Etape(
            "6.5.5.1", f"Longueur effective, flambage selon {axe}", f"L_{{e({axe})}}",
            rf"L_{{e({axe})}} = K_{{e({axe})}} \, L_{{({axe})}}", rf"{cs(K_e)} \times {cs(L_appuis)}",
            L_e(K_e, L_appuis), "mm", "longueur",
        ))
        c_c = r.ajouter_etape(Etape(
            "6.5.5.2.2", f"Élancement, flambage selon {axe}", f"C_{{C({axe})}}",
            rf"C_{{C({axe})}} = L_{{e({axe})}} / {axe} \leq 50", rf"{cs(l_e)} / {cs(dimension)}",
            C_C(l_e, dimension),
        ))
        k_zc = r.ajouter_etape(Etape(
            "6.5.5.2.4", f"Coefficient de dimensions, flambage selon {axe}", f"K_{{Zc({axe})}}",
            rf"K_{{Zc({axe})}} = 6.3 \, ({axe} \, L)^{{-0.13}} \leq 1.3",
            rf"6.3 \times ({cs(dimension)} \times {cs(L)})^{{-0.13}}",
            K_Zc(dimension, L),
        ))
        k_c = r.ajouter_etape(Etape(
            "6.5.5.2.5", f"Coefficient d'élancement, flambage selon {axe}", f"K_{{C({axe})}}",
            rf"K_{{C({axe})}} = \left[1 + \frac{{F_c \, K_{{Zc({axe})}} \, C_{{C({axe})}}^3}}"
            r"{35 \, E_{05} \, K_{SE} \, K_T}\right]^{-1}",
            rf"\left[1 + \frac{{{cs(f_c_corrige)} \times {cs(k_zc)} \times {cs(c_c)}^3}}"
            rf"{{35 \times {cs(E_05)} \times {cs(K_SE)} \times {cs(K_T)}}}\right]^{{-1}}",
            K_C(f_c_corrige, k_zc, c_c, E_05, K_SE, K_T),
        ))
        resistances.append(r.ajouter_etape(Etape(
            "6.5.5.2.4", f"Résistance pondérée, flambage selon {axe}", f"P_{{r({axe})}}",
            rf"P_{{r({axe})}} = \phi \, F_c \, A \, K_{{Zc({axe})}} \, K_{{C({axe})}}",
            rf"0.8 \times {cs(f_c_corrige)} \times {cs(A)} \times {cs(k_zc)} \times {cs(k_c)}",
            P_r(f_c_corrige, A, k_zc, k_c), "N",
        )))

    p_r = r.ajouter_etape(Etape(
        "6.5.5.2.1", "Résistance pondérée (plus petite des deux)", "P_r",
        r"P_r = \min(P_{r(b)} \, ; \, P_{r(d)})",
        rf"\min({cs(resistances[0])} \, ; \, {cs(resistances[1])})",
        min(resistances), "N",
    ))

    if P_f is not None:
        r.verification = verifier_etat_limite_ultime(P_f, p_r / 1000, "P_f", "P_r", "kN", "force")

    return r


def _etapes_de_l_element_massif(
    r: Resultat, axe: str, dimension: float, L: float, K_e: float, L_appuis: float, F_c_corrige: float,
    E_05: float, K_SE: float, K_T: float,
) -> tuple[float, float, float]:
    """
    Étapes de 6.5.5.1 à 6.5.5.2.5 pour un axe de flambage de l'élément (massif ou massif équivalent),
    ajoutées à la trace : L_e, C_C, K_Zc et K_C, avec l'axe entre parenthèses (ex. C_C(b)).

    Args:
        r (Resultat): Trace à compléter.
        axe (str): "b" ou "d" (direction du flambage).
        dimension (float): b (largeur de l'élément, plis compris) ou d, mm.
        L (float): Longueur de l'élément, mm (pour K_Zc).
        K_e (float): Coefficient de longueur effective pour cet axe.
        L_appuis (float): Entraxe des appuis latéraux pour cet axe (L de 6.5.5.1), mm.
        F_c_corrige (float): F_c, MPa.
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa.
        K_SE, K_T (float): Coefficients de correction (K_T des « autres propriétés »).

    Returns:
        tuple[float, float, float]: L_e (mm), K_Zc et K_C de cet axe.
    """
    l_e = r.ajouter_etape(Etape(
        "6.5.5.1", f"Longueur effective, flambage selon {axe}", f"L_{{e({axe})}}",
        rf"L_{{e({axe})}} = K_{{e({axe})}} \, L_{{({axe})}}", rf"{cs(K_e)} \times {cs(L_appuis)}",
        L_e(K_e, L_appuis), "mm", "longueur",
    ))
    c_c = r.ajouter_etape(Etape(
        "6.5.5.2.2", f"Élancement, flambage selon {axe}", f"C_{{C({axe})}}",
        rf"C_{{C({axe})}} = L_{{e({axe})}} / {axe} \leq 50", rf"{cs(l_e)} / {cs(dimension)}",
        C_C(l_e, dimension),
    ))
    k_zc = r.ajouter_etape(Etape(
        "6.5.5.2.4", f"Coefficient de dimensions, flambage selon {axe}", f"K_{{Zc({axe})}}",
        rf"K_{{Zc({axe})}} = 6.3 \, ({axe} \, L)^{{-0.13}} \leq 1.3",
        rf"6.3 \times ({cs(dimension)} \times {cs(L)})^{{-0.13}}",
        K_Zc(dimension, L),
    ))
    k_c = r.ajouter_etape(Etape(
        "6.5.5.2.5", f"Coefficient d'élancement, flambage selon {axe}", f"K_{{C({axe})}}",
        rf"K_{{C({axe})}} = \left[1 + \frac{{F_c \, K_{{Zc({axe})}} \, C_{{C({axe})}}^3}}"
        r"{35 \, E_{05} \, K_{SE} \, K_T}\right]^{-1}",
        rf"\left[1 + \frac{{{cs(F_c_corrige)} \times {cs(k_zc)} \times {cs(c_c)}^3}}"
        rf"{{35 \times {cs(E_05)} \times {cs(K_SE)} \times {cs(K_T)}}}\right]^{{-1}}",
        K_C(F_c_corrige, k_zc, c_c, E_05, K_SE, K_T),
    ))
    return l_e, k_zc, k_c


@enregistrer(EDITION, "6.5.5.4", "Éléments composés en compression")
def verifier_compression_parallele_element_compose(
    largeur_d_un_pli: float,
    nombre_de_plis: int,
    d: float,
    L: float,
    L_selon_b: float,
    L_selon_d: float,
    f_c: float,
    E_05: float,
    assemblage: str,
    K_e_selon_b: float = 1,
    K_e_selon_d: float = 1,
    K_D: float = 1,
    K_H: float = 1,
    K_Sc: float = 1,
    K_T: float = 1,
    K_SE: float = 1,
    P_f: float | None = None,
    source_resistances: str = "Tableaux 6.4 à 6.9",
    source_K_D: str = "Tableau 5.1",
    source_K_e_selon_b: str = "Tableau A.4",
    source_K_e_selon_d: str = "Tableau A.4",
) -> Resultat:
    """
    6.5.5.4 Résistance pondérée à la compression parallèle au fil d'un élément composé de 2 à 5 plis
    cloués, boulonnés ou assemblés par anneaux fendus (p. 70-71), selon les deux axes (6.5.5.2.1).

    Flambage selon b (perpendiculaire aux plis) : P_r(b) = la plus grande de (6.5.5.4.1) :
        - coefficient de réduction (6.5.5.4.2 à 6.5.5.4.4) x P_r de l'élément massif de section
          équivalente (6.5.5.2, avec b = largeur totale) ;
        - résistance combinée des plis considérés comme éléments individuels (C_C avec la largeur
          d'un pli). Si le C_C d'un pli dépasse 50 (6.5.5.2.2), un pli ne peut pas être calculé comme
          élément individuel : cette valeur n'est pas retenue (une note le dit).
    Flambage selon d (axe principal des pièces) : coefficient de réduction omis (6.5.5.4.6, décision
    de l'utilisateur, issue #32) : P_r(d) = P_r de l'élément massif équivalent. La résistance combinée
    des plis selon d donnerait la même valeur (même C_C, même K_Zc, même aire totale).
    P_r = min(P_r(b) ; P_r(d)) (6.5.5.2.1).

    Les exigences d'assemblage ne sont pas vérifiées : elles sont ajoutées aux notes de la trace
    (exigences_de_l_assemblage(), décision de l'utilisateur, issue #32).

    Args:
        largeur_d_un_pli (float): Largeur (épaisseur) d'un pli, mm. Pas de symbole dans la norme.
        nombre_de_plis (int): Nombre de plis, 2 à 5 (6.5.5.4.1). Pas de symbole dans la norme.
        d (float): Hauteur de l'élément, mm.
        L (float): Longueur de l'élément, mm (pour K_Zc).
        L_selon_b (float): L de 6.5.5.1 pour le flambage selon b, mm. Symbole affiché : L_(b).
        L_selon_d (float): L de 6.5.5.1 pour le flambage selon d, mm. Symbole affiché : L_(d).
        f_c (float): Résistance prévue en compression parallèle au fil, MPa.
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa.
        assemblage (str): CLOUS, BOULONS ou ANNEAUX_FENDUS (6.5.5.4.2 à 6.5.5.4.4).
        K_e_selon_b, K_e_selon_d (float, optional): K_e de 6.5.5.1 pour chaque axe. Default to 1.
        K_D, K_H, K_Sc, K_T, K_SE (float, optional): Coefficients de correction. K_H : colonne
            « Poutres composées » du tableau 6.12, 1,00 en compression (décision #7). Default to 1.
        P_f (float | None, optional): Charge de compression axiale pondérée, kN. Default to None.
        source_resistances, source_K_D, source_K_e_selon_b, source_K_e_selon_d (str, optional):
            Sources pour la note de calcul, comme verifier_compression_parallele_au_fil().

    Returns:
        Resultat: Trace du calcul. Résistances en N ; vérification en kN.

    Raises:
        ValueError: Hors de 6.5.5.4.1 (plis), assemblage inconnu, valeur invalide, ou C_C > 50 de
            l'élément (selon b ou selon d).
    """
    # 6.5.5.4.1 : 2 à 5 plis d'au moins 38 mm, sinon calcul refusé (décision de l'utilisateur)
    verifier_les_plis(nombre_de_plis, largeur_d_un_pli)
    # Coefficient de réduction de 6.5.5.4.2 à 6.5.5.4.4 (erreur si l'assemblage est inconnu)
    coefficient = coefficient_de_reduction(assemblage)
    article_de_l_assemblage, description_de_l_assemblage, _ = ASSEMBLAGES[assemblage]
    # b = largeur de l'élément, tous les plis compris (3.2, décision #95)
    b = nombre_de_plis * largeur_d_un_pli  # mm

    r = Resultat(
        NORME, "6.5.5.4", "Résistance à la compression parallèle au fil, élément composé", "colonne"
    )
    for donnee in (
        Donnee("b", "Largeur de l'élément (plis compris)", b, "mm", "dimension"),
        Donnee("", "Largeur d'un pli", largeur_d_un_pli, "mm", "dimension"),  # pas de symbole
        Donnee("", "Nombre de plis", nombre_de_plis),  # pas de symbole dans la norme
        Donnee("", "Assemblage des plis", description_de_l_assemblage, source=article_de_l_assemblage),
        Donnee("d", "Hauteur de l'élément", d, "mm", "dimension"),
        Donnee("L", "Longueur de l'élément", L, "mm", "longueur"),
        Donnee("L_{(b)}", "Entraxe des appuis latéraux, flambage selon b", L_selon_b, "mm",
               "longueur"),
        Donnee("L_{(d)}", "Entraxe des appuis latéraux, flambage selon d", L_selon_d, "mm",
               "longueur"),
        Donnee("K_{e(b)}", "Coefficient de longueur effective", K_e_selon_b, source=source_K_e_selon_b),
        Donnee("K_{e(d)}", "Coefficient de longueur effective", K_e_selon_d, source=source_K_e_selon_d),
        Donnee("f_c", "Résistance prévue en compression parallèle au fil", f_c, "MPa", "contrainte",
               source_resistances),
        Donnee("E_{05}", "Module d'élasticité pour les éléments en compression", E_05, "MPa",
               "contrainte", source_resistances),
        Donnee("K_D", "Coefficient de durée d'application de la charge", K_D, source=source_K_D),
        Donnee("K_H", "Coefficient de système (poutres composées)", K_H, source="Tableau 6.12"),
        Donnee("K_{Sc}", "Coefficient de conditions d'utilisation (compression)", K_Sc,
               source="Tableau 6.10"),
        Donnee("K_T", "Coefficient de traitement", K_T, source="Tableau 6.11"),
        Donnee("K_{SE}", "Coefficient de conditions d'utilisation (module d'élasticité)", K_SE,
               source="Tableau 6.10"),
    ):
        r.ajouter_donnee(donnee)

    f_c_corrige = r.ajouter_etape(Etape(
        "6.5.5.2.4", "Résistance corrigée en compression parallèle au fil", "F_c",
        r"F_c = f_c \, (K_D \, K_H \, K_{Sc} \, K_T)",
        rf"{cs(f_c)} \times ({cs(K_D)} \times {cs(K_H)} \times {cs(K_Sc)} \times {cs(K_T)})",
        F_c(f_c, K_D, K_H, K_Sc, K_T), "MPa", "contrainte",
    ))
    A = b * d  # mm², section brute de l'élément massif équivalent (tous les plis)

    # --- Flambage selon b : perpendiculaire aux plis, coefficient de réduction appliqué ---
    l_e_selon_b, k_zc_selon_b, k_c_selon_b = _etapes_de_l_element_massif(
        r, "b", b, L, K_e_selon_b, L_selon_b, f_c_corrige, E_05, K_SE, K_T
    )
    # P_r de l'élément massif de section équivalente (6.5.5.2.4) : pas de symbole propre dans la
    # norme pour le distinguer du P_r de l'élément composé
    p_r_massif_selon_b = r.ajouter_etape(Etape(
        "6.5.5.2.4", "Élément massif de section équivalente, flambage selon b", "",
        rf"\phi \, F_c \, A \, K_{{Zc(b)}} \, K_{{C(b)}}",
        rf"0.8 \times {cs(f_c_corrige)} \times {cs(A)} \times {cs(k_zc_selon_b)} \times {cs(k_c_selon_b)}",
        P_r(f_c_corrige, A, k_zc_selon_b, k_c_selon_b), "N",
    ))
    reduite = r.ajouter_etape(Etape(
        article_de_l_assemblage,
        f"Résistance de l'élément composé ({description_de_l_assemblage.lower()} : {coefficient:.0%})",
        "", rf"{coefficient:.2f} \times \phi \, F_c \, A \, K_{{Zc(b)}} \, K_{{C(b)}}",
        rf"{coefficient:.2f} \times {cs(p_r_massif_selon_b)}",
        resistance_reduite(coefficient, p_r_massif_selon_b), "N",
    ))

    # Plis considérés comme des éléments individuels (6.5.5.4.1) : même L_e(b), mais C_C et K_Zc avec la
    # largeur d'un pli (note de 6.5.5.4.1 : « dimensions de chacun des éléments constitutifs »)
    combinee = None
    c_c_d_un_pli = l_e_selon_b / largeur_d_un_pli
    if c_c_d_un_pli > 50:
        # 6.5.5.2.2 : C_C <= 50. Un pli ne peut pas être calculé comme un élément individuel : la
        # résistance combinée des plis n'est pas une option. Décision de l'utilisateur (PR #114) : la
        # valeur la plus permissive des deux options est retenue ; l'élément composé (C_C le plus petit,
        # largeur totale b) reste valide et donne P_r(b).
        r.ajouter_note(
            f"Plis considérés comme éléments individuels (6.5.5.4.1), flambage selon b : "
            f"C_C = {cs(l_e_selon_b)} mm / {cs(largeur_d_un_pli)} mm = {c_c_d_un_pli:.2f} > 50 "
            "(6.5.5.2.2). Cette valeur n'est pas permise : la résistance de l'élément composé est retenue."
        )
    else:
        c_c_pli = r.ajouter_etape(Etape(
            "6.5.5.2.2", "Élancement d'un pli (élément individuel), flambage selon b", "",
            r"C_C = L_{e(b)} / \text{largeur d'un pli} \leq 50",
            rf"{cs(l_e_selon_b)} / {cs(largeur_d_un_pli)}",
            C_C(l_e_selon_b, largeur_d_un_pli),
        ))
        k_zc_pli = r.ajouter_etape(Etape(
            "6.5.5.2.4", "Coefficient de dimensions d'un pli, flambage selon b", "",
            r"K_{Zc} = 6.3 \, (\text{largeur d'un pli} \times L)^{-0.13} \leq 1.3",
            rf"6.3 \times ({cs(largeur_d_un_pli)} \times {cs(L)})^{{-0.13}}",
            K_Zc(largeur_d_un_pli, L),
        ))
        k_c_pli = r.ajouter_etape(Etape(
            "6.5.5.2.5", "Coefficient d'élancement d'un pli, flambage selon b", "",
            r"K_C = \left[1 + \frac{F_c \, K_{Zc} \, C_C^3}{35 \, E_{05} \, K_{SE} \, K_T}\right]^{-1}",
            rf"\left[1 + \frac{{{cs(f_c_corrige)} \times {cs(k_zc_pli)} \times {cs(c_c_pli)}^3}}"
            rf"{{35 \times {cs(E_05)} \times {cs(K_SE)} \times {cs(K_T)}}}\right]^{{-1}}",
            K_C(f_c_corrige, k_zc_pli, c_c_pli, E_05, K_SE, K_T),
        ))
        aire_d_un_pli = largeur_d_un_pli * d  # mm²
        p_r_d_un_pli = r.ajouter_etape(Etape(
            "6.5.5.2.4", "Résistance d'un pli (élément individuel), flambage selon b", "",
            r"P_r = \phi \, F_c \, (\text{largeur d'un pli} \times d) \, K_{Zc} \, K_C",
            rf"0.8 \times {cs(f_c_corrige)} \times ({cs(largeur_d_un_pli)} \times {cs(d)}) \times "
            rf"{cs(k_zc_pli)} \times {cs(k_c_pli)}",
            P_r(f_c_corrige, aire_d_un_pli, k_zc_pli, k_c_pli), "N",
        ))
        combinee = r.ajouter_etape(Etape(
            "6.5.5.4.1", "Résistance combinée des plis (éléments individuels), flambage selon b", "",
            r"\text{nombre de plis} \times P_r \text{ d'un pli}",
            rf"{nombre_de_plis} \times {cs(p_r_d_un_pli)}",
            resistance_combinee_des_pieces_individuelles(nombre_de_plis, p_r_d_un_pli), "N",
        ))

    if combinee is None:
        p_r_selon_b = r.ajouter_etape(Etape(
            "6.5.5.4.1", "Résistance pondérée, flambage selon b", "P_{r(b)}",
            r"P_{r(b)} = \text{résistance de l'élément composé}", rf"{cs(reduite)}",
            P_r_element_compose(reduite, None), "N",
        ))
    else:
        p_r_selon_b = r.ajouter_etape(Etape(
            "6.5.5.4.1", "Résistance pondérée, flambage selon b (la plus grande)", "P_{r(b)}",
            r"P_{r(b)} = \max(\text{élément composé} \, ; \, \text{plis individuels})",
            rf"\max({cs(reduite)} \, ; \, {cs(combinee)})",
            P_r_element_compose(reduite, combinee), "N",
        ))

    # --- Flambage selon d : axe principal des pièces, coefficient de réduction omis (6.5.5.4.6) ---
    _, k_zc_selon_d, k_c_selon_d = _etapes_de_l_element_massif(
        r, "d", d, L, K_e_selon_d, L_selon_d, f_c_corrige, E_05, K_SE, K_T
    )
    p_r_selon_d = r.ajouter_etape(Etape(
        "6.5.5.4.6", "Résistance pondérée, flambage selon d (coefficient de réduction omis)", "P_{r(d)}",
        rf"P_{{r(d)}} = \phi \, F_c \, A \, K_{{Zc(d)}} \, K_{{C(d)}}",
        rf"0.8 \times {cs(f_c_corrige)} \times {cs(A)} \times {cs(k_zc_selon_d)} \times {cs(k_c_selon_d)}",
        P_r(f_c_corrige, A, k_zc_selon_d, k_c_selon_d), "N",
    ))

    p_r = r.ajouter_etape(Etape(
        "6.5.5.2.1", "Résistance pondérée (plus petite des deux)", "P_r",
        r"P_r = \min(P_{r(b)} \, ; \, P_{r(d)})",
        rf"\min({cs(p_r_selon_b)} \, ; \, {cs(p_r_selon_d)})",
        min(p_r_selon_b, p_r_selon_d), "N",
    ))

    # Exigences d'assemblage de la norme, que Datum ne vérifie pas (décision de l'utilisateur, #32)
    for note in exigences_de_l_assemblage(assemblage, largeur_d_un_pli, d):
        r.ajouter_note(note)

    if P_f is not None:
        r.verification = verifier_etat_limite_ultime(P_f, p_r / 1000, "P_f", "P_r", "kN", "force")

    return r
