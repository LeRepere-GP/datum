"""
CSA O86:19 - A.6.5.5.3 Éléments en compression assemblés avec cales d'espacement (annexe A, informative,
p. 305-308). Issue #115.

6.5.5.3 (p. 69) : « Les éléments en compression assemblés avec cales d'espacement doivent être calculés
en utilisant les résistances prévues et les coefficients de correction appropriés pour le bois
d'œuvre. » Note : ils « peuvent être calculés conformément à l'article A.6.5.5.3 ».

    A.6.5.5.3.1 Généralités : au moins deux éléments individuels, connecteurs pour bois, cales
    A.6.5.5.3.2 Cales d'espacement intermédiaires et d'extrémité (exigences, en notes)
    A.6.5.5.3.3 Classes de degré de retenue : condition A ou B
    A.6.5.5.3.4 Connecteurs des cales d'espacement d'extrémité (tableau A.5)
    A.6.5.5.3.5.1 P_r = la moindre des valeurs de A.6.5.5.3.5.2 et A.6.5.5.3.5.5
    A.6.5.5.3.5.2 P_r = phi F_c A K_C K_Zc, F_c = f_c (K_D K_Sc K_T) (pas de K_H)
    A.6.5.5.3.5.3 Élancement, C_C <= 80
    A.6.5.5.3.5.4 Coefficient d'élancement, K_C (C_K, K_E, k)
    A.6.5.5.3.5.5 Résistance totale de chaque élément (pièces calculées seules)
    A.6.5.5.3.6 Flexion et charge axiale combinées (en note)

Géométrie (figure A.2, p. 308) : les pièces sont côte à côte dans la direction de b, séparées par les
cales. Le flambage « entre les cales » se fait selon b (C_C = longueur / face étroite d'une pièce,
A.6.5.5.3.5.3) ; le flambage selon d est vérifié avec les pièces seules (C_C = longueur / grande face
d'une pièce, A.6.5.5.3.5.5).

Symboles : la face étroite (épaisseur) d'une pièce, le nombre de pièces et l'épaisseur des cales n'ont
pas de symbole dans la norme (règle de la PR #87) ; ils n'en ont pas ici. La « distance réelle entre les
points de support latéral » (A.6.5.5.3.5.3 et A.6.5.5.3.5.5 ; L de la figure A.2) est affichée L_(b) et
L_(d), comme l'entraxe des appuis latéraux de 6.5.5 : l'axe de flambage est entre parenthèses.

Interprétations :
    - K_Zc : L = longueur de l'élément (décision de l'utilisateur pour 6.5.5.2.4, même définition :
      « longueur de l'élément, mm »).
    - K_T dans C_K et dans K_C c) : K_T des « autres propriétés » (tableau 6.11), le même que dans F_c
      (même décision que pour 6.5.5.2.5).
    - C_C = C_K exactement : branche b). Le français dit « inférieur à C_K » (b) et « supérieur à C_K »
      (c), sans l'égalité ; l'anglais (p. 291) dit « greater than 10 but does not exceed C_K » (b). La
      branche b) donne aussi la valeur la plus petite (conservatrice) à l'égalité.
    - Réponse de l'utilisateur (28 novembre 2026, question 1 de l'issue #115) : Datum ne vérifie pas
      les cales ni les connecteurs ; les exigences de la norme sont affichées en notes (page et note
      PDF), avec la constante du tableau A.5 et la résistance requise des connecteurs comme information.
    - EN ATTENTE DE L'UTILISATEUR (issue #115) : d de K_Zc dans A.6.5.5.3.5.2 (dimension hors tout,
      cales comprises, proposée) ; K_H = 1,00 pour les pièces seules de A.6.5.5.3.5.5 ; l'annexe comme
      méthode de Datum pour 6.5.5.3.
    - Réponse de l'utilisateur (28 novembre 2026, question 2 de l'issue #115) : « Donner l'option en
      fonction de la position des connecteurs ». L'ingénieur entre la distance entre l'extrémité de
      l'élément et le centre des connecteurs de la cale d'extrémité ; Datum en déduit la condition A ou
      B (condition_de_retenue()).
    - L de A.6.5.5.3.3 (« 1/20 de la longueur, L ») : la clause renvoie à la figure A.2, où L = « distance
      entre les points d'appui latéral des éléments en compression assemblés sur cale d'espacement »,
      soit L_(b) ici (flambage entre les cales). Pour un poteau tenu seulement à ses extrémités, L_(b)
      = L.
"""

import math

from moteur.commun.nombres import cs
from moteur.commun.registre import enregistrer
from moteur.commun.resultat import Donnee, Etape, Resultat
from moteur.commun.unites import deux_unites
from moteur.normes.csa_o86_19 import NORME
from moteur.normes.csa_o86_19.ch_5_conception_generale.art_5_1_calculs_aux_etats_limites import (
    verifier_etat_limite_ultime,
)
# Fonctions simples de 6.5.5 réutilisées (mêmes formules, sans les recopier) :
#   - P_r : A.6.5.5.3.5.2 donne P_r = phi F_c A K_C K_Zc, phi = 0,80 pour le bois de sciage, la même
#     formule et le même phi que 6.5.5.2.4 ;
#   - K_Zc : A.6.5.5.3.5.2 donne K_Zc = 6,3 (d L)^-0,13 <= 1,3, la même formule que 6.5.5.2.4 ;
#   - C_C (<= 50) et K_C de 6.5.5.2 : pour les pièces « considérées comme élément simple en
#     compression » (A.6.5.5.3.5.5).
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art_6_5_5,
)

EDITION = "csa_o86_19"

# A.6.5.5.3.1 : « au moins deux éléments individuels » (pas de maximum)
NOMBRE_DE_PIECES_MINIMAL = 2
# A.6.5.5.3.5.3 : C_C « ne doit pas dépasser 80 »
C_C_MAXIMAL = 80

# A.6.5.5.3.3 et A.6.5.5.3.5.4 : condition de retenue -> (description de la figure A.2, K_E)
CONDITION_A = "A"
CONDITION_B = "B"
CONDITIONS = {
    # « le centre des connecteurs [...] doit se trouver à moins de 1/20 de la longueur, L » ; K_E = 2,50
    CONDITION_A: ("connecteurs à moins de L / 20 de l'extrémité de l'élément", 2.50),
    # « entre 1/20 et 1/10 de la longueur, L » ; K_E = 3,00
    CONDITION_B: ("connecteurs entre L / 20 et L / 10 de l'extrémité de l'élément", 3.00),
}

# A.6.5.5.3.5.4 c) : k = 1,8 pour le bois de sciage (2,0 pour le bois lamellé-collé, hors du chapitre 6)
k_BOIS_DE_SCIAGE = 1.8

# Tableau A.5 (p. 307-308) : constante relative aux cales d'espacement d'extrémité, MPa.
# Lignes : C_C de 10 à 60 par bonds de 5 (« 0 à 10 » donne 0,00 ; « 60 à 80 » donne la valeur de 60).
# Colonnes : groupes d'essences, avec les identifiants des tableaux 6.4 à 6.7 (art_6_3.classes()) :
#   "df" = Sapin de Douglas-mélèze, "hf" = Pruche-sapin (N), "spf" = É-P-S, "ns" = Essences nordiques.
TABLEAU_A_5_C_C = (10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)
TABLEAU_A_5 = {
    "df": (0.00, 0.38, 0.79, 1.2, 1.5, 1.9, 2.2, 2.6, 3.0, 3.4, 3.8),
    "hf": (0.00, 0.30, 0.62, 0.92, 1.3, 1.5, 1.9, 2.2, 2.5, 2.8, 3.0),
    "spf": (0.00, 0.26, 0.55, 0.81, 1.1, 1.4, 1.6, 1.9, 2.2, 2.5, 2.6),
    "ns": (0.00, 0.23, 0.47, 0.72, 0.96, 1.2, 1.5, 1.6, 1.9, 2.2, 2.3),
}
GROUPES_DU_TABLEAU_A_5 = {
    "df": "Sapin de Douglas-mélèze",
    "hf": "Pruche-sapin (N)",
    "spf": "É-P-S",
    "ns": "Essences nordiques",
}


# FONCTIONS SIMPLES (dans l'ordre de la norme)
def verifier_les_pieces(nombre_de_pieces: int) -> None:
    """
    A.6.5.5.3.1 Généralités : nombre d'éléments individuels.

    « Les éléments en compression assemblés avec cales d'espacement doivent être constitués d'au moins
    deux éléments individuels assemblés à l'aide de connecteurs pour bois [...] » (p. 305). La norme ne
    fixe pas de maximum. Hors de cette limite, le calcul est refusé (comme pour 6.5.5.4.1, issue #32).

    Args:
        nombre_de_pieces (int): Nombre d'éléments individuels (pièces), sans symbole dans la norme.

    Raises:
        ValueError: S'il y a moins de 2 pièces.
    """
    if nombre_de_pieces < NOMBRE_DE_PIECES_MINIMAL:
        raise ValueError(
            f"Un élément assemblé avec cales d'espacement doit avoir au moins 2 pièces (A.6.5.5.3.1) : "
            f"{nombre_de_pieces} pièce(s). Calcul refusé."
        )


def condition_de_retenue(distance_des_connecteurs: float, L_selon_b: float) -> str:
    """
    A.6.5.5.3.3 Classes de degré de retenue : condition A ou B selon la position des connecteurs.

    « a) Condition A : le centre des connecteurs ou du groupe de connecteurs de la cale d'espacement
    d'extrémité doit se trouver à moins de 1/20 de la longueur, L, mesurée depuis l'extrémité de
    l'élément. b) Condition B : [...] entre 1/20 et 1/10 de la longueur, L [...] » (p. 305 ; anglais,
    p. 290 : « within 1/20 of the length, L »).

    - distance <= L / 20 : condition A. L'anglais « within 1/20 » comprend l'égalité ; la condition A
      donne aussi le K_E le plus petit (conservateur) à la limite.
    - L / 20 < distance <= L / 10 : condition B.
    - distance > L / 10 : aucune classe de la norme (« doivent être classés [...] selon une des
      conditions ») : calcul refusé.

    Args:
        distance_des_connecteurs (float): Distance entre l'extrémité de l'élément et le centre des
            connecteurs (ou du groupe de connecteurs) de la cale d'extrémité, mm. Pas de symbole.
        L_selon_b (float): L de la figure A.2, distance entre les points d'appui latéral, mm.

    Returns:
        str: CONDITION_A ou CONDITION_B.

    Raises:
        ValueError: Si une valeur n'est pas positive ou si la distance dépasse L / 10.
    """
    if distance_des_connecteurs <= 0 or L_selon_b <= 0:
        raise ValueError("La position des connecteurs et L doivent être positives (A.6.5.5.3.3).")
    if distance_des_connecteurs <= L_selon_b / 20:
        return CONDITION_A
    if distance_des_connecteurs <= L_selon_b / 10:
        return CONDITION_B
    raise ValueError(
        f"Connecteurs des cales d'extrémité à {distance_des_connecteurs:g} mm de l'extrémité, plus de "
        f"L / 10 = {L_selon_b / 10:g} mm : ni condition A ni condition B (A.6.5.5.3.3). Calcul refusé."
    )


def K_E(condition: str) -> float:
    """
    A.6.5.5.3.3 et A.6.5.5.3.5.4 Coefficient de retenue d'extrémité, K_E.

    K_E = 2,50 pour la condition A (connecteurs des cales d'extrémité à moins de L/20 de l'extrémité) ;
    K_E = 3,00 pour la condition B (entre L/20 et L/10).

    Args:
        condition (str): CONDITION_A ("A") ou CONDITION_B ("B").

    Returns:
        float: K_E (sans unité).

    Raises:
        ValueError: Si la condition est inconnue.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"Condition de retenue inconnue : {condition!r}. Choix : A ou B (A.6.5.5.3.3).")
    return CONDITIONS[condition][1]


def F_c(f_c: float, K_D: float = 1, K_Sc: float = 1, K_T: float = 1) -> float:
    """
    A.6.5.5.3.5.2 Résistance corrigée en compression parallèle au fil, F_c.

    F_c = f_c (K_D K_Sc K_T)

    Différence avec 6.5.5.2.4 : pas de coefficient de système K_H dans cette formule (p. 306 ; anglais,
    p. 291 : « F_c = f_c (K_D K_Sc K_T) »).

    Args:
        f_c (float): Résistance prévue en compression parallèle au fil, MPa (tableaux 6.4 à 6.9).
        K_D (float, optional): Coefficient de durée d'application de la charge. Default to 1.
        K_Sc (float, optional): Coefficient de conditions d'utilisation (compression parallèle).
            Default to 1.
        K_T (float, optional): Coefficient de traitement (« autres propriétés »). Default to 1.

    Returns:
        float: F_c, MPa.
    """
    return f_c * (K_D * K_Sc * K_T)


def dimension_hors_tout(nombre_de_pieces: int, largeur_d_une_piece: float, epaisseur_des_cales: float) -> float:
    """
    Dimension hors tout de l'élément assemblé dans la direction de b (pièces et cales), pour le d de K_Zc
    de A.6.5.5.3.5.2 (« dimension de l'élément dans la direction du flambage »). Pas de symbole.

    EN ATTENTE DE L'UTILISATEUR (issue #115) : lecture proposée, « l'élément » = l'élément assemblé
    (comme A = « aire de la section transversale totale de l'élément »). Cette dimension est la plus
    grande des lectures possibles, donc K_Zc le plus petit (conservateur).

    dimension = nombre de pièces x face étroite d'une pièce + (nombre de pièces - 1) x épaisseur des cales

    Args:
        nombre_de_pieces (int): Nombre de pièces.
        largeur_d_une_piece (float): Face étroite d'une pièce (dans la direction de b), mm.
        epaisseur_des_cales (float): Épaisseur des cales (vide entre deux pièces), mm.

    Returns:
        float: Dimension hors tout, mm.

    Raises:
        ValueError: Si une dimension n'est pas positive.
    """
    if largeur_d_une_piece <= 0 or epaisseur_des_cales <= 0:
        raise ValueError("La largeur des pièces et l'épaisseur des cales doivent être positives (A.6.5.5.3).")
    return nombre_de_pieces * largeur_d_une_piece + (nombre_de_pieces - 1) * epaisseur_des_cales


def C_C(distance_entre_les_supports_lateraux: float, face_etroite_d_une_piece: float) -> float:
    """
    A.6.5.5.3.5.3 Élancement, C_C.

    C_C = distance réelle entre les points de support latéral de l'élément / face étroite d'un élément
    individuel, <= 80 (p. 306 ; anglais, p. 291 : « least dimension of an individual member »).

    La distance est réelle : pas de coefficient de longueur effective K_e (la retenue des extrémités est
    prise en compte par K_E dans C_K).

    Args:
        distance_entre_les_supports_lateraux (float): Distance réelle entre les points de support
            latéral (L de la figure A.2), mm. Symbole affiché : L_(b).
        face_etroite_d_une_piece (float): Face étroite d'une pièce (épaisseur, direction de b), mm.

    Returns:
        float: C_C.

    Raises:
        ValueError: Si une valeur n'est pas positive ou si C_C > 80.
    """
    if distance_entre_les_supports_lateraux <= 0 or face_etroite_d_une_piece <= 0:
        raise ValueError("La distance et la face étroite doivent être positives (A.6.5.5.3.5.3).")

    c_c = distance_entre_les_supports_lateraux / face_etroite_d_une_piece
    if c_c > C_C_MAXIMAL:
        raise ValueError(f"L'élancement (Cc = {c_c:.2f}) ne doit pas dépasser 80 (A.6.5.5.3.5.3).")

    return c_c


def C_K(F_c: float, E_05: float, K_E: float, K_SE: float = 1, K_T: float = 1) -> float:
    """
    A.6.5.5.3.5.4 b) Élancement de transition, C_K.

    C_K = racine( 0,76 E_05 K_SE K_E K_T / F_c )

    Args:
        F_c (float): F_c = f_c (K_D K_Sc K_T), MPa (A.6.5.5.3.5.2).
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa (tableaux 6.4 à 6.7 pour
            le bois classé visuellement ; 0,82E pour le bois classé mécaniquement par résistance).
        K_E (float): Coefficient de retenue d'extrémité (2,50 ou 3,00, K_E()).
        K_SE (float, optional): Coefficient de conditions d'utilisation relatif au module d'élasticité.
            Default to 1.
        K_T (float, optional): Coefficient de traitement des « autres propriétés », le même que dans
            F_c. Default to 1.

    Returns:
        float: C_K.
    """
    return math.sqrt(0.76 * E_05 * K_SE * K_E * K_T / F_c)


def K_C(
    C_C: float, C_K: float, F_c: float, E_05: float, K_E: float, K_SE: float = 1, K_T: float = 1
) -> float:
    """
    A.6.5.5.3.5.4 Coefficient d'élancement, K_C.

    a) C_C <= 10 :            K_C = 1,00
    b) 10 < C_C <= C_K :      K_C = 1 - (1/3) (C_C / C_K)^4
    c) C_K < C_C <= 80 :      K_C = E_05 K_SE K_E K_T / (k C_C^2 F_c), k = 1,8 (bois de sciage)

    Égalité C_C = C_K : branche b). L'anglais (p. 291) dit « greater than 10 but does not exceed C_K »
    (le français, « inférieur à C_K », ne couvre pas l'égalité). La branche b) donne aussi la plus petite
    valeur à l'égalité : 2/3 = 0,667, contre 1 / (1,8 x 0,76) = 0,731 en c).

    Args:
        C_C (float): Élancement (A.6.5.5.3.5.3).
        C_K (float): Élancement de transition (C_K()).
        F_c (float): F_c = f_c (K_D K_Sc K_T), MPa.
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa.
        K_E (float): Coefficient de retenue d'extrémité.
        K_SE (float, optional): Coefficient de conditions d'utilisation (module d'élasticité). Default to 1.
        K_T (float, optional): Coefficient de traitement des « autres propriétés ». Default to 1.

    Returns:
        float: K_C.

    Raises:
        ValueError: Si C_C n'est pas positif ou dépasse 80.
    """
    if C_C <= 0 or C_C > C_C_MAXIMAL:
        raise ValueError(f"Cc = {C_C:.2f} doit être positif et ne pas dépasser 80 (A.6.5.5.3.5.3).")

    if C_C <= 10:  # a) « si C_C ne dépasse pas 10 »
        return 1.00
    if C_C <= C_K:  # b) « supérieur à 10, mais [...] ne dépasse pas C_K » (anglais)
        return 1 - (1 / 3) * (C_C / C_K) ** 4
    # c) « supérieur à C_K, mais ne dépasse pas 80 »
    return E_05 * K_SE * K_E * K_T / (k_BOIS_DE_SCIAGE * C_C**2 * F_c)


def C_C_d_une_piece_seule(distance_entre_les_supports_lateraux: float, grande_face_d_une_piece: float) -> float:
    """
    A.6.5.5.3.5.5 Élancement d'une pièce considérée comme élément simple en compression.

    C_C = distance réelle entre les points de support latéral de l'élément / grande face d'un élément
    individuel (p. 307 ; anglais, p. 292 : « larger dimension of an individual member »).

    La pièce est un « élément simple en compression » : la limite de 6.5.5.2.2 (C_C <= 50) s'applique
    (art_6_5_5.C_C()).

    Args:
        distance_entre_les_supports_lateraux (float): Distance réelle entre les points de support
            latéral pour ce flambage, mm. Symbole affiché : L_(d).
        grande_face_d_une_piece (float): Grande face d'une pièce (d), mm.

    Returns:
        float: C_C.

    Raises:
        ValueError: Si une valeur n'est pas positive ou si C_C > 50.
    """
    return art_6_5_5.C_C(distance_entre_les_supports_lateraux, grande_face_d_une_piece)


def P_r_element_assemble(resistance_de_l_element_assemble: float, resistance_des_pieces: float) -> float:
    """
    A.6.5.5.3.5.1 Résistance pondérée à la compression parallèle au fil, P_r.

    « [...] doit être la moindre des valeurs calculées aux articles A.6.5.5.3.5.2 et A.6.5.5.3.5.5 »
    (p. 306). Contrairement aux éléments composés (6.5.5.4.1 : « la plus grande »), c'est le minimum.

    Args:
        resistance_de_l_element_assemble (float): P_r de A.6.5.5.3.5.2, N.
        resistance_des_pieces (float): Somme des P_r des pièces seules (A.6.5.5.3.5.5), N.

    Returns:
        float: P_r, N.
    """
    return min(resistance_de_l_element_assemble, resistance_des_pieces)


def constante_du_tableau_A_5(C_C: float, groupe_d_essences: str) -> float:
    """
    Tableau A.5 Constante relative aux cales d'espacement d'extrémité, MPa (A.6.5.5.3.4, p. 307-308).

    « Les constantes pour les valeurs intermédiaires de C_C peuvent être obtenues par simple
    interpolation » (note * du tableau) : interpolation linéaire entre les lignes. C_C de 0 à 10 :
    0,00 ; C_C de 60 à 80 : valeur de la ligne « 60 à 80 ». Pas de symbole dans la norme.

    Args:
        C_C (float): Élancement de l'élément assemblé (A.6.5.5.3.5.3).
        groupe_d_essences (str): "df", "hf", "spf" ou "ns" (identifiants des tableaux 6.4 à 6.7).

    Returns:
        float: Constante, MPa.

    Raises:
        ValueError: Si le groupe d'essences n'est pas au tableau A.5 ou si C_C n'est pas entre 0 et 80.
    """
    if groupe_d_essences not in TABLEAU_A_5:
        raise ValueError(
            f"Groupe d'essences absent du tableau A.5 : {groupe_d_essences!r}. "
            f"Choix : {sorted(TABLEAU_A_5)}."
        )
    if C_C < 0 or C_C > C_C_MAXIMAL:
        raise ValueError(f"Cc = {C_C:.2f} doit être entre 0 et 80 (tableau A.5).")

    constantes = TABLEAU_A_5[groupe_d_essences]
    if C_C <= TABLEAU_A_5_C_C[0]:  # ligne « 0 à 10 »
        return constantes[0]
    if C_C >= TABLEAU_A_5_C_C[-1]:  # ligne « 60 à 80 »
        return constantes[-1]
    # Interpolation linéaire entre les deux lignes qui encadrent C_C
    for i in range(len(TABLEAU_A_5_C_C) - 1):
        c_c_bas, c_c_haut = TABLEAU_A_5_C_C[i], TABLEAU_A_5_C_C[i + 1]
        if c_c_bas <= C_C <= c_c_haut:
            fraction = (C_C - c_c_bas) / (c_c_haut - c_c_bas)
            return constantes[i] + fraction * (constantes[i + 1] - constantes[i])
    raise AssertionError("C_C hors du tableau A.5")  # inatteignable : C_C est entre 10 et 60 ici


def resistance_requise_des_connecteurs(aire_d_une_piece: float, constante: float) -> float:
    """
    A.6.5.5.3.4 Résistance pondérée requise des connecteurs de chaque paire de surfaces de contact entre
    une cale d'extrémité et une pièce, à chaque extrémité. Pas de symbole dans la norme.

    « [...] une résistance pondérée, en newtons, correspondant à la section transversale requise, en
    mm², d'un des éléments individuels multipliée par la constante [...] précisée au tableau A.5. »

    Information seulement : Datum ne calcule pas encore la résistance des connecteurs (article 12).

    Args:
        aire_d_une_piece (float): Section transversale d'une pièce, mm².
        constante (float): Constante du tableau A.5, MPa.

    Returns:
        float: Résistance pondérée requise, N (mm² x MPa = N).
    """
    return aire_d_une_piece * constante


def exigences_des_cales(
    condition: str, distance_des_connecteurs: float, L_selon_b: float, largeur_d_une_piece: float,
    epaisseur_des_cales: float,
    resistance_requise: float | None,
) -> list[str]:
    """
    Exigences de A.6.5.5.3.1 à A.6.5.5.3.4 et A.6.5.5.3.6, en notes.

    Réponse de l'utilisateur (28 novembre 2026), comme pour les éléments composés (#32) : Datum ne
    vérifie pas les cales ni les connecteurs ; les exigences de la norme sont affichées (page et note
    PDF) et l'ingénieur s'assure qu'elles sont respectées. Les valeurs qui ne dépendent que des données
    sont calculées pour aider (ex. L / 20).

    Args:
        condition (str): CONDITION_A ou CONDITION_B (condition_de_retenue()).
        distance_des_connecteurs (float): Distance entre l'extrémité et le centre des connecteurs, mm.
        L_selon_b (float): L de la figure A.2 (distance entre les points d'appui latéral), mm.
        largeur_d_une_piece (float): Face étroite (épaisseur) d'une pièce, mm.
        epaisseur_des_cales (float): Épaisseur des cales entrée, mm.
        resistance_requise (float | None): Résistance pondérée requise des connecteurs (A.6.5.5.3.4), N.
            None si le groupe d'essences n'est pas au tableau A.5.

    Returns:
        list[str]: Une note par exigence, dans l'ordre de la norme.
    """
    K_E(condition)  # erreur si la condition est inconnue
    vingtieme = L_selon_b / 20  # mm
    dixieme = L_selon_b / 10  # mm
    position_entree = deux_unites(distance_des_connecteurs, 'longueur')
    if condition == CONDITION_A:
        position = (
            f"centre des connecteurs de chaque cale d'extrémité à {position_entree} de l'extrémité de "
            f"l'élément, au plus L / 20 = {deux_unites(vingtieme, 'longueur')} : condition A (K_E = 2.50)"
        )
    else:
        position = (
            f"centre des connecteurs de chaque cale d'extrémité à {position_entree} de l'extrémité de "
            f"l'élément, entre L / 20 = {deux_unites(vingtieme, 'longueur')} et L / 10 = "
            f"{deux_unites(dixieme, 'longueur')} : condition B (K_E = 3.00)"
        )
    # A.6.5.5.3.2 c) : épaisseur des cales >= épaisseur des pièces, ou entre la moitié et l'épaisseur
    # des pièces avec une longueur de cale ajustée. Cas sous la moitié : non permis.
    if epaisseur_des_cales >= largeur_d_une_piece:
        epaisseur = "l'épaisseur entrée respecte ce minimum"
    elif epaisseur_des_cales >= largeur_d_une_piece / 2:
        epaisseur = (
            "l'épaisseur entrée est entre la moitié et l'épaisseur des pièces : la longueur de chaque cale "
            "doit être augmentée selon cet alinéa"
        )
    else:
        epaisseur = "ATTENTION : l'épaisseur entrée est inférieure à la moitié de l'épaisseur des pièces"
    if resistance_requise is None:
        connecteurs = (
            "A.6.5.5.3.4 : les connecteurs de chaque paire de surfaces de contact entre une cale "
            "d'extrémité et une pièce, à chaque extrémité, doivent avoir une résistance pondérée d'au "
            "moins l'aire d'une pièce x la constante du tableau A.5 (groupe d'essences absent du tableau : "
            "non calculée)."
        )
    else:
        connecteurs = (
            "A.6.5.5.3.4 : les connecteurs de chaque paire de surfaces de contact entre une cale "
            "d'extrémité et une pièce, à chaque extrémité, doivent avoir une résistance pondérée d'au "
            f"moins {deux_unites(resistance_requise / 1000, 'force')} (aire d'une pièce x constante du "
            "tableau A.5, voir les étapes). Datum ne vérifie pas encore les connecteurs (article 12)."
        )
    return [
        "Datum ne vérifie pas les cales d'espacement ni les connecteurs : l'ingénieur doit s'assurer que "
        "les exigences suivantes sont respectées.",
        "A.6.5.5.3.1 : au moins deux pièces assemblées à l'aide de connecteurs pour bois, avec des cales "
        "d'espacement intermédiaires et d'extrémité conformes à A.6.5.5.3.2 à A.6.5.5.3.4.",
        "A.6.5.5.3.2 a) : cales d'extrémité placées de manière à respecter, dans les cales et les pièces, "
        "les distances de rive et d'extrémité et les espacements de l'article 12 ; dans une ferme, un nœud "
        "contreventé latéralement peut être considéré comme l'extrémité de l'élément.",
        "A.6.5.5.3.2 b) : une cale intermédiaire à 10 % près du centre de la longueur (sans connecteurs "
        "requis) ; s'il en faut plus d'une, distance entre deux cales d'au plus la moitié de la distance "
        "entre les centres des connecteurs des cales d'extrémité, et connecteurs selon a).",
        f"A.6.5.5.3.2 c) : épaisseur des cales d'au moins celle des pièces "
        f"({deux_unites(largeur_d_une_piece, 'dimension')}), ou entre la moitié et cette épaisseur si la "
        f"longueur de chaque cale est ajustée ; {epaisseur} "
        f"({deux_unites(epaisseur_des_cales, 'dimension')}). Cales assez grandes pour la résistance de "
        "l'article 12.",
        f"A.6.5.5.3.3 : {position}.",
        connecteurs,
        "A.6.5.5.3.6 : en flexion et charge axiale combinées, 6.5.9 ne s'applique que si la flexion "
        "s'exerce parallèlement à la grande face de chaque pièce.",
    ]


# VÉRIFICATION
@enregistrer(EDITION, "A.6.5.5.3", "Éléments en compression assemblés avec cales d'espacement")
def verifier_compression_element_avec_cales_d_espacement(
    largeur_d_une_piece: float,
    nombre_de_pieces: int,
    d: float,
    epaisseur_des_cales: float,
    L: float,
    L_selon_b: float,
    L_selon_d: float,
    f_c: float,
    E_05: float,
    distance_des_connecteurs: float,
    K_D: float = 1,
    K_Sc: float = 1,
    K_T: float = 1,
    K_SE: float = 1,
    groupe_d_essences: str | None = None,
    P_f: float | None = None,
    source_resistances: str = "Tableaux 6.4 à 6.9",
    source_K_D: str = "Tableau 5.1",
) -> Resultat:
    """
    A.6.5.5.3 Résistance pondérée à la compression parallèle au fil d'un élément assemblé avec cales
    d'espacement (annexe A, informative ; 6.5.5.3, p. 69).

    1. Élément assemblé, flambage selon b (A.6.5.5.3.5.2 à A.6.5.5.3.5.4) :
       P_r = phi F_c A K_C K_Zc, A = aire totale des pièces, C_C = L_(b) / face étroite d'une pièce.
    2. Pièces seules, flambage selon d (A.6.5.5.3.5.5) : somme des P_r de chaque pièce considérée comme
       élément simple (6.5.5.2), C_C = L_(d) / grande face d'une pièce.
    3. P_r = la moindre des deux (A.6.5.5.3.5.1).
    Les exigences des cales et des connecteurs sont ajoutées aux notes (exigences_des_cales()).

    Args:
        largeur_d_une_piece (float): Face étroite (épaisseur) d'une pièce, dans la direction de b, mm.
            Pas de symbole dans la norme.
        nombre_de_pieces (int): Nombre de pièces, au moins 2 (A.6.5.5.3.1). Pas de symbole.
        d (float): Grande face d'une pièce (hauteur de l'élément), mm.
        epaisseur_des_cales (float): Épaisseur des cales (vide entre deux pièces), mm. Pas de symbole.
        L (float): Longueur de l'élément, mm (K_Zc ; L / 20 et L / 10 de A.6.5.5.3.3).
        L_selon_b (float): Distance réelle entre les points de support latéral pour le flambage selon b
            (A.6.5.5.3.5.3), mm. Symbole affiché : L_(b).
        L_selon_d (float): Distance réelle entre les points de support latéral pour le flambage selon d
            (A.6.5.5.3.5.5), mm. Symbole affiché : L_(d).
        f_c (float): Résistance prévue en compression parallèle au fil, MPa.
        E_05 (float): Module d'élasticité pour les éléments en compression, MPa.
        distance_des_connecteurs (float): Distance entre l'extrémité de l'élément et le centre des
            connecteurs de la cale d'extrémité, mm ; donne la condition A ou B (A.6.5.5.3.3). Pas de
            symbole.
        K_D, K_Sc, K_T, K_SE (float, optional): Coefficients de correction. Pas de K_H (A.6.5.5.3.5.2).
            Default to 1.
        groupe_d_essences (str | None, optional): "df", "hf", "spf" ou "ns", pour la constante du
            tableau A.5 (information). None : constante non calculée. Default to None.
        P_f (float | None, optional): Charge de compression axiale pondérée, kN. Default to None.
        source_resistances, source_K_D (str, optional): Sources pour la note de calcul, comme
            art_6_5_5.verifier_compression_parallele_au_fil().

    Returns:
        Resultat: Trace du calcul. Résistances en N ; vérification en kN.

    Raises:
        ValueError: Moins de 2 pièces, connecteurs à plus de L / 10, valeur invalide, C_C > 80 (élément assemblé)
            ou C_C > 50 (pièce seule).
    """
    # A.6.5.5.3.1 : au moins 2 pièces, sinon calcul refusé
    verifier_les_pieces(nombre_de_pieces)
    # A.6.5.5.3.3 : condition A ou B selon la position des connecteurs (refus au-delà de L / 10)
    condition = condition_de_retenue(distance_des_connecteurs, L_selon_b)
    k_e = K_E(condition)
    description_de_la_condition = CONDITIONS[condition][0]

    r = Resultat(
        NORME, "A.6.5.5.3", "Résistance à la compression parallèle au fil, élément avec cales d'espacement",
        "colonne",
    )
    for donnee in (
        Donnee("", "Face étroite d'une pièce", largeur_d_une_piece, "mm", "dimension"),  # pas de symbole
        Donnee("", "Nombre de pièces", nombre_de_pieces),  # pas de symbole dans la norme
        Donnee("d", "Grande face d'une pièce (hauteur de l'élément)", d, "mm", "dimension"),
        Donnee("", "Épaisseur des cales", epaisseur_des_cales, "mm", "dimension"),  # pas de symbole
        Donnee("L", "Longueur de l'élément", L, "mm", "longueur"),
        Donnee("L_{(b)}", "Distance réelle entre les points de support latéral, flambage selon b",
               L_selon_b, "mm", "longueur"),
        Donnee("L_{(d)}", "Distance réelle entre les points de support latéral, flambage selon d",
               L_selon_d, "mm", "longueur"),
        Donnee("", "Position des connecteurs des cales d'extrémité (depuis l'extrémité)",
               distance_des_connecteurs, "mm", "longueur"),  # pas de symbole dans la norme
        Donnee("", "Degré de retenue", f"Condition {condition} : {description_de_la_condition}",
               source="A.6.5.5.3.3"),
        Donnee("f_c", "Résistance prévue en compression parallèle au fil", f_c, "MPa", "contrainte",
               source_resistances),
        Donnee("E_{05}", "Module d'élasticité pour les éléments en compression", E_05, "MPa",
               "contrainte", source_resistances),
        Donnee("K_D", "Coefficient de durée d'application de la charge", K_D, source=source_K_D),
        Donnee("K_{Sc}", "Coefficient de conditions d'utilisation (compression)", K_Sc,
               source="Tableau 6.10"),
        Donnee("K_T", "Coefficient de traitement", K_T, source="Tableau 6.11"),
        Donnee("K_{SE}", "Coefficient de conditions d'utilisation (module d'élasticité)", K_SE,
               source="Tableau 6.10"),
    ):
        r.ajouter_donnee(donnee)

    # F_c sans K_H (A.6.5.5.3.5.2), utilisé pour l'élément assemblé et pour les pièces seules
    f_c_corrige = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.2", "Résistance corrigée en compression parallèle au fil", "F_c",
        r"F_c = f_c \, (K_D \, K_{Sc} \, K_T)",
        rf"{cs(f_c)} \times ({cs(K_D)} \times {cs(K_Sc)} \times {cs(K_T)})",
        F_c(f_c, K_D, K_Sc, K_T), "MPa", "contrainte",
    ))
    aire_d_une_piece = largeur_d_une_piece * d  # mm²
    A = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.2", "Aire de la section transversale totale de l'élément", "A",
        r"A = \text{nombre de pièces} \times \text{face étroite d'une pièce} \times d",
        rf"{nombre_de_pieces} \times {cs(largeur_d_une_piece)} \times {cs(d)}",
        nombre_de_pieces * aire_d_une_piece, "mm²", "aire",
    ))

    # --- 1. Élément assemblé, flambage selon b (A.6.5.5.3.5.2 à A.6.5.5.3.5.4) ---
    c_c_selon_b = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.3", "Élancement de l'élément assemblé, flambage selon b", "C_{C(b)}",
        r"C_{C(b)} = L_{(b)} / \text{face étroite d'une pièce} \leq 80",
        rf"{cs(L_selon_b)} / {cs(largeur_d_une_piece)}",
        C_C(L_selon_b, largeur_d_une_piece),
    ))
    # d de K_Zc : dimension hors tout dans la direction du flambage (EN ATTENTE, issue #115)
    d_hors_tout = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.2", "Dimension de l'élément dans la direction du flambage (hors tout, cales comprises)",
        "", r"\text{nombre de pièces} \times \text{face étroite} + (\text{nombre de pièces} - 1) \times "
        r"\text{épaisseur des cales}",
        rf"{nombre_de_pieces} \times {cs(largeur_d_une_piece)} + {nombre_de_pieces - 1} \times "
        rf"{cs(epaisseur_des_cales)}",
        dimension_hors_tout(nombre_de_pieces, largeur_d_une_piece, epaisseur_des_cales), "mm", "dimension",
    ))
    k_zc_selon_b = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.2", "Coefficient de dimensions, flambage selon b", "K_{Zc(b)}",
        r"K_{Zc(b)} = 6.3 \, (\text{dimension hors tout} \times L)^{-0.13} \leq 1.3",
        rf"6.3 \times ({cs(d_hors_tout)} \times {cs(L)})^{{-0.13}}",
        art_6_5_5.K_Zc(d_hors_tout, L),
    ))
    c_k = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.4", "Élancement de transition", "C_K",
        r"C_K = \sqrt{\frac{0.76 \, E_{05} \, K_{SE} \, K_E \, K_T}{F_c}}",
        rf"\sqrt{{\frac{{0.76 \times {cs(E_05)} \times {cs(K_SE)} \times {cs(k_e)} \times {cs(K_T)}}}"
        rf"{{{cs(f_c_corrige)}}}}}",
        C_K(f_c_corrige, E_05, k_e, K_SE, K_T),
    ))
    # Formule de K_C selon la branche de A.6.5.5.3.5.4 qui s'applique
    if c_c_selon_b <= 10:
        formule_k_c = r"C_{C(b)} \leq 10 : K_{C(b)} = 1.00"
        substitution_k_c = rf"{cs(c_c_selon_b)} \leq 10"
    elif c_c_selon_b <= c_k:
        formule_k_c = r"10 < C_{C(b)} \leq C_K : K_{C(b)} = 1 - \frac{1}{3} \left(\frac{C_{C(b)}}{C_K}\right)^4"
        substitution_k_c = rf"1 - \frac{{1}}{{3}} \left(\frac{{{cs(c_c_selon_b)}}}{{{cs(c_k)}}}\right)^4"
    else:
        formule_k_c = (
            r"C_K < C_{C(b)} \leq 80 : K_{C(b)} = \frac{E_{05} \, K_{SE} \, K_E \, K_T}{k \, C_{C(b)}^2 \, F_c}"
            r", \; k = 1.8"
        )
        substitution_k_c = (
            rf"\frac{{{cs(E_05)} \times {cs(K_SE)} \times {cs(k_e)} \times {cs(K_T)}}}"
            rf"{{1.8 \times {cs(c_c_selon_b)}^2 \times {cs(f_c_corrige)}}}"
        )
    k_c_selon_b = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.4", "Coefficient d'élancement, flambage selon b", "K_{C(b)}",
        formule_k_c, substitution_k_c,
        K_C(c_c_selon_b, c_k, f_c_corrige, E_05, k_e, K_SE, K_T),
    ))
    p_r_assemble = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.2", "Résistance de l'élément assemblé, flambage selon b", "P_{r(b)}",
        r"P_{r(b)} = \phi \, F_c \, A \, K_{C(b)} \, K_{Zc(b)}",
        rf"0.8 \times {cs(f_c_corrige)} \times {cs(A)} \times {cs(k_c_selon_b)} \times {cs(k_zc_selon_b)}",
        art_6_5_5.P_r(f_c_corrige, A, k_zc_selon_b, k_c_selon_b), "N",
    ))

    # --- 2. Pièces seules, flambage selon d (A.6.5.5.3.5.5), chacune par 6.5.5.2 ---
    # F_c : le même (K_H = 1,00, EN ATTENTE, issue #115) ; K_Zc avec d (grande face) et L ;
    # K_C de 6.5.5.2.5 avec le K_T des « autres propriétés ».
    c_c_selon_d = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.5", "Élancement d'une pièce seule, flambage selon d", "C_{C(d)}",
        r"C_{C(d)} = L_{(d)} / d \leq 50", rf"{cs(L_selon_d)} / {cs(d)}",
        C_C_d_une_piece_seule(L_selon_d, d),
    ))
    k_zc_selon_d = r.ajouter_etape(Etape(
        "6.5.5.2.4", "Coefficient de dimensions d'une pièce, flambage selon d", "K_{Zc(d)}",
        r"K_{Zc(d)} = 6.3 \, (d \, L)^{-0.13} \leq 1.3",
        rf"6.3 \times ({cs(d)} \times {cs(L)})^{{-0.13}}",
        art_6_5_5.K_Zc(d, L),
    ))
    k_c_selon_d = r.ajouter_etape(Etape(
        "6.5.5.2.5", "Coefficient d'élancement d'une pièce, flambage selon d", "K_{C(d)}",
        r"K_{C(d)} = \left[1 + \frac{F_c \, K_{Zc(d)} \, C_{C(d)}^3}{35 \, E_{05} \, K_{SE} \, K_T}\right]^{-1}",
        rf"\left[1 + \frac{{{cs(f_c_corrige)} \times {cs(k_zc_selon_d)} \times {cs(c_c_selon_d)}^3}}"
        rf"{{35 \times {cs(E_05)} \times {cs(K_SE)} \times {cs(K_T)}}}\right]^{{-1}}",
        art_6_5_5.K_C(f_c_corrige, k_zc_selon_d, c_c_selon_d, E_05, K_SE, K_T),
    ))
    p_r_d_une_piece = r.ajouter_etape(Etape(
        "6.5.5.2.4", "Résistance d'une pièce seule, flambage selon d", "",
        r"\phi \, F_c \, (\text{face étroite} \times d) \, K_{Zc(d)} \, K_{C(d)}",
        rf"0.8 \times {cs(f_c_corrige)} \times ({cs(largeur_d_une_piece)} \times {cs(d)}) \times "
        rf"{cs(k_zc_selon_d)} \times {cs(k_c_selon_d)}",
        art_6_5_5.P_r(f_c_corrige, aire_d_une_piece, k_zc_selon_d, k_c_selon_d), "N",
    ))
    # Toutes les pièces sont identiques : la somme est le nombre de pièces x P_r d'une pièce
    p_r_des_pieces = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.5", "Somme des résistances des pièces seules, flambage selon d", "P_{r(d)}",
        r"P_{r(d)} = \text{nombre de pièces} \times \text{résistance d'une pièce}",
        rf"{nombre_de_pieces} \times {cs(p_r_d_une_piece)}",
        nombre_de_pieces * p_r_d_une_piece, "N",
    ))

    # --- 3. La moindre des deux (A.6.5.5.3.5.1) ---
    p_r = r.ajouter_etape(Etape(
        "A.6.5.5.3.5.1", "Résistance pondérée (la moindre des deux)", "P_r",
        r"P_r = \min(P_{r(b)} \, ; \, P_{r(d)})",
        rf"\min({cs(p_r_assemble)} \, ; \, {cs(p_r_des_pieces)})",
        P_r_element_assemble(p_r_assemble, p_r_des_pieces), "N",
    ))

    # --- Information : connecteurs des cales d'extrémité (A.6.5.5.3.4, tableau A.5) ---
    resistance_requise = None
    if groupe_d_essences in TABLEAU_A_5:
        constante = r.ajouter_etape(Etape(
            "Tableau A.5",
            f"Constante des cales d'extrémité ({GROUPES_DU_TABLEAU_A_5[groupe_d_essences]}, "
            "interpolée selon C_C(b))", "",
            r"\text{constante}(C_{C(b)})", rf"C_{{C(b)}} = {cs(c_c_selon_b)}",
            constante_du_tableau_A_5(c_c_selon_b, groupe_d_essences), "MPa", "contrainte",
        ))
        resistance_requise = r.ajouter_etape(Etape(
            "A.6.5.5.3.4", "Résistance pondérée requise des connecteurs (information)", "",
            r"\text{aire d'une pièce} \times \text{constante}",
            rf"({cs(largeur_d_une_piece)} \times {cs(d)}) \times {cs(constante)}",
            resistance_requise_des_connecteurs(aire_d_une_piece, constante), "N",
        ))

    # Exigences des cales et des connecteurs, que Datum ne vérifie pas (réponse de l'utilisateur, 28 nov.)
    for note in exigences_des_cales(
        condition, distance_des_connecteurs, L_selon_b, largeur_d_une_piece, epaisseur_des_cales,
        resistance_requise,
    ):
        r.ajouter_note(note)

    if P_f is not None:
        r.verification = verifier_etat_limite_ultime(P_f, p_r / 1000, "P_f", "P_r", "kN", "force")

    return r
