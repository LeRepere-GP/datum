"""
Moteur de calcul de Datum, par Le Repère Ingénierie.

Le moteur est indépendant de l'interface : il ne dépend ni de Streamlit, ni de l'API. Voir
ARCHITECTURE.md pour l'organisation (commun/, normes/<norme_edition>/).
"""

# Version de Datum (décision de l'utilisateur : 0.1.0 pour commencer), affichée dans l'application et
# dans la note de calcul PDF. Format MAJEUR.MINEUR.CORRECTIF : CORRECTIF pour un correctif, MINEUR pour
# une fonction ajoutée, MAJEUR pour une étape majeure. Claude ajuste le numéro dans ses PR au fil des
# avancements ; les versions majeures (1.0.0, 2.0.0…) sont décidées par l'utilisateur seulement (PR #109).
VERSION = "0.2.1"  # 0.2.1 : correctif, termine la PR #112 (titre de la note tiré de la boîte « Pièce »)
