"""
Page Bois de sciage : tableau « Résumé » des vérifications (issue #85, simplifié par datum-retours #22).

Colonnes : Article | Charge pondérée | Résistance pondérée | Ratio | Statut. Toutes les vérifications
offertes au compte, dans l'ordre des onglets ; charges et résistances en métrique seulement.
2x6 S-P-F n° 1/n° 2 (38 mm x 140 mm) : f_cp = 5.3 MPa, K_D = K_Scp = K_T = K_B = K_Zcp = 1.00 (voir
test_page_k_d.py et test_page_compression_perpendiculaire.py).
"""

from unittest import mock

import acces
from tests.test_acces import _connecte

ORDRE_DES_ONGLETS = ["6.5.3", "6.5.4.3", "6.5.4.4", "6.5.5", "6.5.6.2", "6.5.6.3"]


def _resume(at):
    return [m.value for m in at.markdown if m.value.startswith("| Article")]


def _lignes(at):
    """Lignes du tableau, sans l'en-tête et la ligne d'alignement, découpées en cellules."""
    (tableau,) = _resume(at)
    return [[c.strip() for c in l.strip("|").split("|")] for l in tableau.splitlines()[2:]]


def _ligne(at, article):
    return next(l for l in _lignes(at) if l[0].strip("*") == article)


def _entrer(at, cle, texte):
    [n for n in at.text_input if n.key == cle][0].set_value(texte)
    return at


def test_en_tete_du_tableau():
    # datum-retours #22 : plus de colonne « Vérification » (titre), l'article seulement
    at = _connecte("admin", "mot-admin")
    (tableau,) = _resume(at)
    assert tableau.splitlines()[0] == "| Article | Charge pondérée | Résistance pondérée | Ratio | Statut |"


def test_toutes_les_verifications_sans_charge():
    """
    Aucune charge entrée : une ligne par vérification offerte, dans l'ordre des onglets.
    - 6.5.3 et 6.5.4.3 : la résistance est calculée sans charge (M_r, V_r) -> « Charge manquante », la
      résistance affichée, charge et ratio « — » (décision de l'utilisateur, datum-retours #22) ;
    - 6.5.4.4 (pas d'entaille), 6.5.5 (pas de L), 6.5.6.2 et 6.5.6.3 (pas de longueur d'appui) : pas de
      trace -> « Non calculé », tout à « — ».
    Aucune vérification faite : aucune ligne en gras.
    """
    at = _connecte("admin", "mot-admin")
    assert not at.exception
    lignes = _lignes(at)
    assert [l[0] for l in lignes] == ORDRE_DES_ONGLETS
    for article in ("6.5.3", "6.5.4.3"):
        article_, charge, resistance, ratio, statut = _ligne(at, article)
        assert (charge, ratio, statut) == ("—", "—", ":gray[Charge manquante]")
        assert resistance.startswith("$M_r$ = " if article == "6.5.3" else "$V_r$ = ")
    for article in ("6.5.4.4", "6.5.5", "6.5.6.2", "6.5.6.3"):
        assert _ligne(at, article)[1:] == ["—", "—", "—", ":gray[Non calculé]"]
    assert not any("**" in c for l in lignes for c in l)


def test_verification_conforme_qui_gouverne():
    """
    L_b = 89 mm : A_b = 38 mm x 89 mm = 3382 mm² ;
    Q_r = 0.8 x 5.3 MPa x 3382 mm² x 1.00 x 1.00 = 14 339.68 N -> 14.3 kN ;
    R_f = 10 kN : 10 kN / 14.340 kN = 69.74 % -> Conforme.
    V_f = 1 kN : V_r = 0.9 x 1.5 MPa x (1.00 x 1.00 x 1.00 x 1.00) x 2/3 x (38 mm x 140 mm) x 1.4 (K_Zv)
    = 6703 N -> 6.70 kN ; 1 kN / 6.703 kN = 14.92 % -> Conforme.
    69.74 % > 14.92 % : 6.5.6.2 gouverne (seule ligne en gras).
    """
    at = _connecte("admin", "mot-admin")
    _entrer(at, "cp_support_length", "89 mm")
    _entrer(at, "cp_rf", "10 kN")
    _entrer(at, "cis_vf", "1 kN").run()
    assert not at.exception
    assert _ligne(at, "6.5.6.2") == [
        "**6.5.6.2**", "**$R_f$ = 10.0 kN**", "**$Q_r$ = 14.3 kN**", "**69.74 %**", "**:green[✔ Conforme]**"
    ]
    assert _ligne(at, "6.5.4.3") == [
        "6.5.4.3", "$V_f$ = 1.00 kN", "$V_r$ = 6.70 kN", "14.92 %", ":green[✔ Conforme]"
    ]
    # Une seule ligne en gras : celle qui gouverne
    assert sum(any("**" in c for c in l) for l in _lignes(at)) == 1
    # 6.5.6.3 (pas de charge près de l'appui) : toujours « Non calculé »
    assert _ligne(at, "6.5.6.3")[4] == ":gray[Non calculé]"
    assert any("Résumé" == s.value for s in at.subheader)


def test_verification_non_conforme():
    """R_f = 20 kN : 20 kN / 14.340 kN = 139.47 % -> Non conforme (et gouverne)."""
    at = _connecte("admin", "mot-admin")
    _entrer(at, "cp_support_length", "89 mm")
    _entrer(at, "cp_rf", "20 kN").run()
    assert _ligne(at, "6.5.6.2") == [
        "**6.5.6.2**", "**$R_f$ = 20.0 kN**", "**$Q_r$ = 14.3 kN**", "**139.47 %**",
        "**:red[✖ Non conforme]**",
    ]


def test_ratio_exactement_1():
    """R_f = Q_r = 14 339.68 N = 14.33968 kN : ratio 100.00 %, état limite respecté (5.1.2, « ne dépasse pas »)."""
    at = _connecte("admin", "mot-admin")
    _entrer(at, "cp_support_length", "89 mm")
    _entrer(at, "cp_rf", "14.33968 kN").run()
    assert _ligne(at, "6.5.6.2")[3:] == ["**100.00 %**", "**:green[✔ Conforme]**"]


def test_metrique_seulement_meme_en_imperial():
    """
    datum-retours #22 : charge et résistance en métrique seulement dans le résumé, même avec la bascule
    des charges en impérial (les onglets gardent les deux unités, PR #99).
    R_f = 2248.1 lb x 4.4482216 N/lb = 10 000 N = 10.0 kN.
    """
    at = _connecte("admin", "mot-admin")
    [b for b in at.sidebar.get("button_group") if b.key == "unites_charges"][0].set_value("Impérial").run()
    _entrer(at, "cp_support_length", "89 mm")
    _entrer(at, "cp_rf", "2248.1 lb").run()
    assert not at.exception
    ligne = _ligne(at, "6.5.6.2")
    assert ligne[1] == "**$R_f$ = 10.0 kN**" and ligne[2] == "**$Q_r$ = 14.3 kN**"
    assert not any("lb" in c for l in _lignes(at) for c in l)


def test_verifications_non_offertes_absentes():
    # datum-retours #22 : une vérification qui n'est pas offerte au compte est absente du tableau
    with mock.patch.dict(acces.ACCES, {acces.LANTIER: frozenset({"compression_perpendiculaire", "note_pdf"})}):
        at = _connecte("lantier", "mot-lantier")
    assert not at.exception
    assert [l[0] for l in _lignes(at)] == ["6.5.6.2", "6.5.6.3"]


def test_pas_de_resume_sans_la_note():
    # Le Résumé est lié à la note de calcul (acces « note_pdf ») : sans elle, pas de tableau
    with mock.patch.dict(acces.ACCES, {acces.LANTIER: frozenset({"compression_perpendiculaire"})}):
        at = _connecte("lantier", "mot-lantier")
    assert not at.exception
    assert _resume(at) == []


def test_page_resume_de_la_note_comme_le_tableau():
    """
    datum-retours #22 : la note reçoit les mêmes lignes que le tableau (toutes les vérifications
    offertes), sauf une vérification faite mais décochée dans « Vérifications à inclure » : elle n'est
    pas dans la note, donc pas dans son résumé.
    """
    from moteur.commun import note_de_calcul

    with mock.patch.object(note_de_calcul, "produire_pdf", return_value=b"%PDF") as produire:
        at = _connecte("admin", "mot-admin")
        _entrer(at, "cp_support_length", "89 mm")
        _entrer(at, "cp_rf", "10 kN")
        _entrer(at, "cis_vf", "1 kN").run()
        assert not at.exception
        offertes = produire.call_args.kwargs["verifications_offertes"]
        assert [prevue.article for _, prevue, _ in offertes] == ORDRE_DES_ONGLETS
        # Décocher le cisaillement : absent de la note et de son résumé
        [c for c in at.checkbox if c.key == "note_Cisaillement (6.5.4.3)"][0].uncheck().run()
        assert not at.exception
        offertes = produire.call_args.kwargs["verifications_offertes"]
        assert [prevue.article for _, prevue, _ in offertes] == ["6.5.3", "6.5.4.4", "6.5.5", "6.5.6.2", "6.5.6.3"]
