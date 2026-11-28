"""Tests du résumé des vérifications (moteur/commun/resume.py, issue #85)."""

import math

from moteur.commun.resultat import Resultat, Verification
from moteur.commun.resume import resume


def trace(titre, article, charge, resistance, symboles=("P_f", "P_r")):
    """Trace minimale avec sa vérification finale (ratio calculé à la main dans chaque test)."""
    ratio = charge / resistance if resistance > 0 else math.inf
    return Resultat(
        "CSA O86:19", article, titre,
        verification=Verification(
            "5.1.2", symboles[0], charge, symboles[1], resistance, ratio, ratio <= 1.0, "kN", "force"
        ),
    )


def test_une_ligne_par_verification_faite():
    # Cisaillement : 5 kN / 10 kN = 0.50 ; compression : 8 kN / 10 kN = 0.80 (gouverne)
    lignes = resume([
        ("P-1", trace("Cisaillement", "6.5.4.3", 5.0, 10.0, ("V_f", "V_r"))),
        ("P-1", trace("Compression parallèle au fil", "6.5.5", 8.0, 10.0)),
    ])
    assert [l.titre for l in lignes] == ["Cisaillement", "Compression parallèle au fil"]  # ordre reçu
    l = lignes[0]
    assert (l.element, l.article, l.symbole_charge, l.symbole_resistance) == ("P-1", "6.5.4.3", "V_f", "V_r")
    assert (l.charge, l.resistance, l.unite, l.grandeur) == (5.0, 10.0, "kN", "force")
    assert l.ratio == 0.5 and l.respecte
    assert [l.gouverne for l in lignes] == [False, True]


def test_trace_sans_verification_ignoree():
    # Charge pondérée pas encore entrée : pas de ligne
    sans = Resultat("CSA O86:19", "6.5.3", "Flexion")
    lignes = resume([("P-1", sans, True), ("P-1", trace("Compression", "6.5.5", 2.0, 10.0), False)])
    assert [l.titre for l in lignes] == ["Compression"]
    assert lignes[0].gouverne  # seule vérification : elle gouverne


def test_aucune_verification():
    assert resume([]) == []
    assert resume([("P-1", Resultat("CSA O86:19", "6.5.3", "Flexion"))]) == []


def test_ratios_egaux_la_premiere_gouverne():
    # 10 kN / 10 kN = 1.00 (au seuil : respecté) dans les deux cas
    lignes = resume([("A", trace("Un", "6.5.5", 10.0, 10.0)), ("B", trace("Deux", "6.5.6", 10.0, 10.0))])
    assert [l.gouverne for l in lignes] == [True, False]
    assert all(l.respecte for l in lignes)


def test_depassee_et_resistance_nulle():
    # 12 kN / 10 kN = 1.20 (dépassé) ; résistance nulle : ratio infini, qui gouverne
    lignes = resume([
        ("A", trace("Dépassée", "6.5.5", 12.0, 10.0)),
        ("A", trace("Nulle", "6.5.6", 1.0, 0.0)),
    ])
    assert not lignes[0].respecte and math.isclose(lignes[0].ratio, 1.2)
    assert math.isinf(lignes[1].ratio) and lignes[1].gouverne and not lignes[1].respecte


def test_page_resume_de_la_note():
    """Page résumé au début de la note de calcul PDF, à partir de 2 vérifications."""
    from moteur.commun.note_de_calcul import EnTete, donnees_de_la_note, produire_pdf
    from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
        art_6_5_3_resistance_au_moment_de_flexion as art_6_5_3,
    )

    entete = EnTete("Client", "Projet", "Adresse", "2026-001", "2026-11-23", "Ingénieur", "000000")

    def flexion(M_f=None):
        # 38 x 235 mm, f_b = 11.8 MPa, K_Zb = 1.1 : M_r = 4 085 877 N·mm (test de 6.5.3)
        return art_6_5_3.verifier_flexion(
            38, 235, 11.8, K_Zb=1.1, support_lateral_aux_appuis=True, rive_comprimee_maintenue=True,
            M_f=M_f,
        )

    # Une seule vérification : sa page est déjà son résumé
    assert donnees_de_la_note([("2x10", flexion(4.0))], entete)["resume"] == []
    # M_r = 4.086 kN·m : 4.0 kN·m -> 97.90 % ; 5.0 kN·m -> 122.37 % (gouverne, dépassé)
    note = donnees_de_la_note([("2x10", flexion(4.0)), ("2x10", flexion()), ("2x10", flexion(5.0))], entete)
    lignes = note["resume"]
    assert [l["indice"] for l in lignes] == [0, 2]  # renvoi à la page de chaque vérification
    assert [l["ratio"] for l in lignes] == ["97.90 %", "122.37 %"]
    assert [l["statut"] for l in lignes] == ["Conforme", "Non conforme"]
    assert [l["gouverne"] for l in lignes] == [False, True]
    # Métrique seulement dans le résumé (PR #93) ; 4 085 877 N·mm = 4.09 kN·m (3 chiffres significatifs)
    assert lignes[0]["charge"] == "4.00 kN·m"
    assert lignes[0]["resistance"] == "4.09 kN·m"
    assert (lignes[0]["symbole_charge"], lignes[0]["article"]) == ("M_f", "6.5.3")
    pdf = produire_pdf([("2x10", flexion(4.0)), ("2x10", flexion(5.0))], entete)
    assert pdf.startswith(b"%PDF")


# --- Toutes les vérifications offertes, avec leur statut (datum-retours #22) ---

from moteur.commun.resultat import Etape  # noqa: E402
from moteur.commun.resume import (  # noqa: E402
    CHARGE_MANQUANTE,
    CONFORME,
    NON_CALCULE,
    NON_CONFORME,
    VerificationPrevue,
    resume_des_verifications_offertes,
)

APPUI = VerificationPrevue("Compression perpendiculaire au fil à l'appui", "6.5.6.2", "R_f", "Q_r", "kN", "force")
FLEXION = VerificationPrevue("Résistance au moment de flexion", "6.5.3", "M_f", "M_r", "kN·m", "moment")
CISAILLEMENT = VerificationPrevue("Résistance au cisaillement", "6.5.4.3", "V_f", "V_r", "kN", "force")


def trace_sans_charge(prevue, valeur, unite):
    """Trace dont la résistance est calculée (étape du symbole de la résistance), sans charge entrée."""
    r = Resultat("CSA O86:19", prevue.article, prevue.titre)
    r.ajouter_etape(Etape(prevue.article, "Résistance pondérée", prevue.symbole_resistance, "", "", valeur, unite))
    return r


def test_les_quatre_statuts():
    """
    Une ligne par vérification reçue, dans l'ordre reçu :
    - 6.5.3 : M_r = 4 085 877 N·mm, pas de M_f -> « Charge manquante », M_r = 4 085 877 / 1 000 000 =
      4.085877 kN·m ;
    - 6.5.4.3 : pas de trace -> « Non calculé » ;
    - 6.5.6.2 : 10 kN / 14.34 kN = 0.6974 -> « Conforme » ;
    - 6.5.5 : 12 kN / 10 kN = 1.20 -> « Non conforme », et gouverne (ratio le plus élevé).
    """
    compression = trace("Compression parallèle au fil", "6.5.5", 12.0, 10.0)
    appui = trace(APPUI.titre, "6.5.6.2", 10.0, 14.34, ("R_f", "Q_r"))
    lignes = resume_des_verifications_offertes([
        ("P-1", FLEXION, trace_sans_charge(FLEXION, 4_085_877.0, "N·mm")),
        ("P-1", CISAILLEMENT, None),
        ("P-1", APPUI, appui),
        ("P-1", VerificationPrevue("Compression", "6.5.5", "P_f", "P_r", "kN", "force"), compression),
    ])
    assert [l.article for l in lignes] == ["6.5.3", "6.5.4.3", "6.5.6.2", "6.5.5"]
    assert [l.statut for l in lignes] == [CHARGE_MANQUANTE, NON_CALCULE, CONFORME, NON_CONFORME]
    manquante, non_calcule, conforme, non_conforme = lignes
    # Charge manquante : résistance convertie dans l'unité du résumé, rien d'autre
    assert math.isclose(manquante.resistance, 4.085877) and manquante.unite == "kN·m"
    assert (manquante.charge, manquante.ratio, manquante.respecte) == (None, None, None)
    assert (manquante.symbole_charge, manquante.symbole_resistance) == ("M_f", "M_r")
    # Non calculé : symboles de la vérification prévue, aucune valeur
    assert (non_calcule.charge, non_calcule.resistance, non_calcule.ratio) == (None, None, None)
    assert (non_calcule.titre, non_calcule.symbole_resistance) == ("Résistance au cisaillement", "V_r")
    # Vérifications faites : valeurs de la trace telles quelles
    assert (conforme.charge, conforme.resistance) == (10.0, 14.34)
    assert math.isclose(non_conforme.ratio, 1.2) and non_conforme.respecte is False
    assert [l.gouverne for l in lignes] == [False, False, False, True]


def test_charge_manquante_en_newtons():
    # Q_r = 14 339.68 N / 1000 = 14.33968 kN
    (ligne,) = resume_des_verifications_offertes([("", APPUI, trace_sans_charge(APPUI, 14_339.68, "N"))])
    assert math.isclose(ligne.resistance, 14.33968) and ligne.statut == CHARGE_MANQUANTE
    assert not ligne.gouverne  # pas de vérification faite : aucune ligne ne gouverne


def test_resistance_deja_dans_l_unite_du_resume():
    (ligne,) = resume_des_verifications_offertes([("", APPUI, trace_sans_charge(APPUI, 14.3, "kN"))])
    assert ligne.resistance == 14.3


def test_unite_impossible_a_convertir():
    # Mieux vaut une erreur qu'une résistance affichée dans la mauvaise unité
    import pytest

    with pytest.raises(ValueError, match="impossible à convertir"):
        resume_des_verifications_offertes([("", APPUI, trace_sans_charge(APPUI, 14.3, "MPa"))])


def test_trace_sans_l_etape_de_la_resistance():
    # Trace sans l'étape Q_r (ne devrait pas arriver) : « Non calculé », pas d'erreur
    (ligne,) = resume_des_verifications_offertes([("", APPUI, Resultat("CSA O86:19", "6.5.6.2", "Appui"))])
    assert ligne.statut == NON_CALCULE and ligne.resistance is None


def test_aucune_verification_offerte():
    assert resume_des_verifications_offertes([]) == []


def test_ratios_egaux_parmi_les_offertes():
    # 10 kN / 10 kN = 1.00 deux fois (au seuil : respecté) : la première gouverne ; la ligne « Non
    # calculé » placée avant ne change rien
    lignes = resume_des_verifications_offertes([
        ("", CISAILLEMENT, None),
        ("", APPUI, trace("Un", "6.5.6.2", 10.0, 10.0)),
        ("", APPUI, trace("Deux", "6.5.6.2", 10.0, 10.0)),
    ])
    assert [l.gouverne for l in lignes] == [False, True, False]
    assert [l.statut for l in lignes] == [NON_CALCULE, CONFORME, CONFORME]


def test_page_resume_de_la_note_avec_les_verifications_offertes():
    """
    Note de calcul (datum-retours #22) : la page résumé a les mêmes lignes que le tableau de l'interface.
    M_r = 4 085 877 N·mm = 4.09 kN·m (test de 6.5.3) ; 4.0 kN·m -> 97.90 % ; 5.0 kN·m -> 122.37 %.
    """
    from moteur.commun.note_de_calcul import EnTete, donnees_de_la_note, produire_pdf
    from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
        art_6_5_3_resistance_au_moment_de_flexion as art_6_5_3,
    )

    entete = EnTete("Client", "Projet", "Adresse", "2026-001", "2026-11-27", "Ingénieur", "000000")

    def flexion(M_f=None):
        return art_6_5_3.verifier_flexion(
            38, 235, 11.8, K_Zb=1.1, support_lateral_aux_appuis=True, rive_comprimee_maintenue=True,
            M_f=M_f,
        )

    faite_1, faite_2, sans_charge = flexion(4.0), flexion(5.0), flexion()
    offertes = [
        ("2x10", FLEXION, faite_1),
        ("2x10", CISAILLEMENT, None),
        ("2x10", FLEXION, sans_charge),
        ("2x10", FLEXION, faite_2),
    ]
    note = donnees_de_la_note([("2x10", faite_1), ("2x10", faite_2)], entete, verifications_offertes=offertes)
    lignes = note["resume"]
    assert [l["statut"] for l in lignes] == ["Conforme", "Non calculé", "Charge manquante", "Non conforme"]
    # Renvoi à la page : seulement pour les vérifications qui sont dans la note
    assert [l["indice"] for l in lignes] == [0, None, None, 1]
    assert [l["ratio"] for l in lignes] == ["97.90 %", "—", "—", "122.37 %"]
    assert [l["charge"] for l in lignes] == ["4.00 kN·m", "—", "—", "5.00 kN·m"]
    assert [l["resistance"] for l in lignes] == ["4.09 kN·m", "—", "4.09 kN·m", "4.09 kN·m"]
    assert [l["gouverne"] for l in lignes] == [False, False, False, True]
    # Une seule vérification faite dans la note : pas de page résumé (sa page est déjà son résumé)
    assert donnees_de_la_note([("2x10", faite_1)], entete, verifications_offertes=offertes[:3])["resume"] == []
    # Le PDF se produit avec les lignes « — » (gabarit Typst)
    pdf = produire_pdf([("2x10", faite_1), ("2x10", faite_2)], entete, verifications_offertes=offertes)
    assert pdf.startswith(b"%PDF")
