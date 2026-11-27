"""Tests des projets et du fichier « .datum » (moteur/commun/projet.py, issue #85, étape 2, option A)."""

import json
import math

import pytest

from moteur import VERSION
from moteur.commun.note_de_calcul import EnTete
from moteur.commun.projet import (
    FORMAT,
    Element,
    FichierInvalide,
    Projet,
    depuis_json,
    resume_du_projet,
    vers_json,
)
from moteur.commun.resultat import Resultat
from tests.moteur.commun.test_resume import trace


def _projet():
    return Projet(
        en_tete=EnTete(client="Client A", projet="Garage", dossier="2026-042", ingenieur="G. P."),
        elements=[
            Element("Poutre P-1 : 2-2x10", "csa_o86_19", {
                "essence": "S-P-F", "classe": "n° 1/n° 2", "plis": 2, "b": 38.0, "d": 235.0,  # mm
                "milieu_humide": False, "M_f": 12.5, "V_f": None,  # kN·m ; kN (pas encore entré)
            }),
            Element("Poteau C-1", "csa_o86_19", {"L": 2438.4, "P_f": 20.0}),  # mm ; kN
        ],
    )


# --- Aller-retour ---

def test_aller_retour_projet_fichier_projet():
    projet = _projet()
    assert depuis_json(vers_json(projet)) == projet


def test_aller_retour_fichier_projet_fichier():
    texte = vers_json(_projet())
    assert vers_json(depuis_json(texte)) == texte
    assert depuis_json(texte.encode("utf-8")) == _projet()  # fichier téléversé : octets


def test_fichier_sans_resultats():
    """Option A : seulement les données d'entrée, jamais de résultat (ni ratio, ni trace)."""
    contenu = json.loads(vers_json(_projet()))
    assert set(contenu) == {"type", "format", "version", "en_tete", "elements"}
    assert contenu["format"] == FORMAT == 1
    assert contenu["version"] == VERSION == "0.1.1"  # version de Datum qui a écrit le fichier (PR #106)
    assert all(set(e) == {"nom", "edition", "entrees"} for e in contenu["elements"])
    assert contenu["elements"][0]["edition"] == "csa_o86_19"
    assert "°" in vers_json(_projet())  # accents gardés tels quels (UTF-8), fichier lisible


def test_projet_vide():
    assert depuis_json(vers_json(Projet())) == Projet()


# --- Fichiers refusés ---

def _contenu(**changements):
    contenu = json.loads(vers_json(_projet()))
    contenu.update(changements)
    return json.dumps(contenu)


@pytest.mark.parametrize("texte, raison", [
    ("pas du JSON", "JSON illisible"),
    (b"\xff\xfe\x00", "JSON illisible"),
    ("[1, 2]", "pas un projet Datum"),
    ('{"format": 1}', "pas un projet Datum"),
    (_contenu(type="autre"), "pas un projet Datum"),
    (_contenu(format=None), "n'indique pas son format"),
    (_contenu(format=True), "n'indique pas son format"),
    (_contenu(format=FORMAT + 1), "version plus récente"),
    (_contenu(format=0), "Format de fichier inconnu"),
    (_contenu(version=1), "Version de Datum invalide"),
    (_contenu(en_tete={"inconnu": "x"}), "En-tête du projet invalide"),
    (_contenu(en_tete={"client": 3}), "chaque champ doit être un texte"),
    (_contenu(elements={}), "Liste des éléments invalide"),
    (_contenu(elements=[{"nom": "P-1"}]), "Élément 1 incomplet"),
    (_contenu(elements=[{"nom": " ", "edition": "csa_o86_19", "entrees": {}}]), "nom manquant"),
    (_contenu(elements=[{"nom": "P-1", "edition": "csa_o86_99", "entrees": {}}]), "édition de norme inconnue"),
    (_contenu(elements=[{"nom": "P-1", "edition": 19, "entrees": {}}]), "édition de norme inconnue"),
    (_contenu(elements=[{"nom": "P-1", "edition": "csa_o86_19", "entrees": []}]), "entrées invalides"),
    (_contenu(elements=[{"nom": "P-1", "edition": "csa_o86_19", "entrees": {"b": [38]}}]), "entrée 'b' invalide"),
    (_contenu(elements=[{"nom": "P-1", "edition": "csa_o86_19", "entrees": {"b": {"x": 1}}}]), "entrée 'b' invalide"),
    ('{"type": "datum-projet", "format": 1, "elements": [{"nom": "P-1", "edition": "csa_o86_19", '
     '"entrees": {"b": NaN}}]}', "JSON illisible"),
    ('{"type": "datum-projet", "format": 1, "elements": [{"nom": "P-1", "edition": "csa_o86_19", '
     '"entrees": {"b": Infinity}}]}', "JSON illisible"),
])
def test_fichier_invalide_refuse(texte, raison):
    with pytest.raises(FichierInvalide, match=raison):
        depuis_json(texte)


def test_deuxieme_element_invalide_refuse_tout_le_fichier():
    contenu = json.loads(vers_json(_projet()))
    contenu["elements"][1]["edition"] = "inconnue"
    with pytest.raises(FichierInvalide, match="Élément 2 « Poteau C-1 »"):
        depuis_json(json.dumps(contenu))


def test_ecriture_refuse_un_element_invalide():
    with pytest.raises(FichierInvalide, match="nombre infini"):
        vers_json(Projet(elements=[Element("P-1", "csa_o86_19", {"b": math.inf})]))
    with pytest.raises(FichierInvalide, match="nom manquant"):
        vers_json(Projet(elements=[Element("", "csa_o86_19")]))


# --- Résumé du projet : une ligne par élément ---

def test_resume_une_ligne_par_element():
    """
    P-1 : cisaillement 5 kN / 10 kN = 0.50, flexion 9 kN·m / 10 kN·m = 0.90 -> la flexion gouverne P-1.
    C-1 : compression 6 kN / 10 kN = 0.60. Le projet est gouverné par P-1 (0.90 > 0.60).
    """
    lignes = resume_du_projet([
        ("P-1", [trace("Cisaillement", "6.5.4.3", 5.0, 10.0), trace("Flexion", "6.5.3", 9.0, 10.0)]),
        ("C-1", [trace("Compression", "6.5.5", 6.0, 10.0)]),
    ])
    assert [(l.element, l.titre, l.ratio) for l in lignes] == [("P-1", "Flexion", 0.9), ("C-1", "Compression", 0.6)]
    assert [l.gouverne for l in lignes] == [True, False]


def test_resume_element_sans_verification_ignore():
    lignes = resume_du_projet([
        ("P-1", [Resultat("CSA O86:19", "6.5.3", "Flexion")]),  # charge pas encore entrée
        ("P-2", []),
        ("C-1", [trace("Compression", "6.5.5", 6.0, 10.0)]),
    ])
    assert [l.element for l in lignes] == ["C-1"] and lignes[0].gouverne


def test_resume_ratios_egaux_et_resistance_nulle():
    # Ratios égaux (0.50 et 0.50) : le premier élément gouverne
    egaux = resume_du_projet([("A", [trace("X", "6.5.3", 5.0, 10.0)]), ("B", [trace("Y", "6.5.5", 5.0, 10.0)])])
    assert [l.gouverne for l in egaux] == [True, False]
    # Résistance nulle : ratio infini, il gouverne toujours
    nulle = resume_du_projet([("A", [trace("X", "6.5.3", 50.0, 10.0)]), ("B", [trace("Y", "6.5.5", 1.0, 0.0)])])
    assert math.isinf(nulle[1].ratio) and [l.gouverne for l in nulle] == [False, True]


def test_resume_dans_un_element_ratio_exactement_1():
    """Ratio = 1.00 exactement (10 kN / 10 kN) : respecté (5.1.2), et il gouverne l'élément."""
    (ligne,) = resume_du_projet([("P-1", [trace("A", "6.5.3", 9.99, 10.0), trace("B", "6.5.5", 10.0, 10.0)])])
    assert ligne.titre == "B" and ligne.ratio == 1.0 and ligne.respecte and ligne.gouverne


def test_resume_vide():
    assert resume_du_projet([]) == []


def test_fichier_sans_version_accepte():
    """La version est une information seulement : un fichier sans elle s'ouvre quand même."""
    contenu = json.loads(vers_json(_projet()))
    del contenu["version"]
    assert depuis_json(json.dumps(contenu)) == _projet()
