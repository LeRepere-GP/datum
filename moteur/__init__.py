"""
Moteur de calcul de Datum, par Le Repère Ingénierie.

Le moteur est indépendant de l'interface : il ne dépend ni de Streamlit, ni de l'API. Voir
ARCHITECTURE.md pour l'organisation (commun/, normes/<norme_edition>/).
"""

# Version de Datum (décision de l'utilisateur : 0.1.0 pour commencer), affichée dans l'application et
# dans la note de calcul PDF. Format MAJEUR.MINEUR.CORRECTIF : CORRECTIF pour un correctif, MINEUR pour
# une fonction ajoutée, MAJEUR pour un changement incompatible (ex. fichiers de projet).
VERSION = "0.1.0"
