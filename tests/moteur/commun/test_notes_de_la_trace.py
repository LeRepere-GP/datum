"""Notes de la trace (Resultat.notes, issue #32) : interface et note de calcul PDF."""

import re

from moteur.commun.note_de_calcul import EnTete, donnees_de_la_note, produire_pdf
from moteur.commun.resultat import Resultat
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art_6_5_5,
)

ENTETE = EnTete("Client", "Projet", "Adresse", "D-1", "2026-11-27", "Ingénieur", "123")


def _compose(P_f=5.0):
    # 3-2x6 boulonnés, L = 3000 mm, L_(b) = 1500 mm, L_(d) = 3000 mm, P_f en kN
    return art_6_5_5.verifier_compression_parallele_element_compose(
        largeur_d_un_pli=38, nombre_de_plis=3, d=140, L=3000, L_selon_b=1500, L_selon_d=3000,
        f_c=11.5, E_05=6500, assemblage=art_6_5_5.BOULONS, P_f=P_f,
    )


def test_resultat_sans_notes_par_defaut():
    r = Resultat("CSA O86:19", "6.5.5", "Test")
    assert r.notes == []
    r.ajouter_note("Une note.")
    assert r.notes == ["Une note."]
    # Chaque Resultat a sa propre liste (pas de liste partagée entre les traces)
    assert Resultat("CSA O86:19", "6.5.5", "Autre").notes == []


def test_notes_dans_les_donnees_de_la_note():
    r = _compose()
    note = donnees_de_la_note([("3-2x6", r)], ENTETE)
    assert note["resultats"][0]["notes"] == r.notes
    assert note["resultats"][0]["notes"][0].startswith("Datum ne vérifie pas")
    assert note["resultats"][0]["article"] == "6.5.5.4"
    assert note["resultats"][0]["figure_svg"] is not None
    assert note["resultats"][0]["icone_svg"] is not None


def test_pdf_avec_notes():
    pages = re.compile(rb"/Type\s*/Page(?!s)")
    pdf = produire_pdf([("3-2x6", _compose())], ENTETE)
    assert pdf.startswith(b"%PDF")
    # Les notes suivent les étapes dans les mêmes colonnes : 2 pages pour ce calcul (pas une 3e page)
    assert len(pages.findall(pdf)) == 2
