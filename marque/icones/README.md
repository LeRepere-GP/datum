# Icônes des types de calcul (issue #62) : proposition

Une icône SVG par type de calcul, dessinée au trait (64 x 64), sans texte. Couleurs de Le Repère par
défaut : principale `#233614` (élément, appuis, déformée) et accent `#9E5A00` (charges). À l'affichage,
elles seront remplacées par les couleurs du compte (`couleurs.toml`).

Icônes : flexion, cisaillement, cisaillement à l'entaille (6.5.4.4, figure 6.1 : entaille à la rive
en traction, longueur e jusqu'au centre de l'appui, fissure en pointillé au coin rentrant), compression parallèle,
compression perpendiculaire (6.5.6.2 : réaction de l'appui seulement, par-dessous), compression près
d'un appui (6.5.6.3, figure 6.2 : réaction de l'appui et charge d'un autre élément appuyé sur le dessus), traction, flexion et charge axiale.

Petites icônes : appuis en triangles ; l'élément appuyé sur le dessus (compression près d'un appui)
est hachuré. Grandes figures : une pièce de bois vue en bout porte un X (figure 6.1 de la norme) et les
appuis sont hachurés.

Aperçu : `apercu.png`. Style validé (issue #62).

Utilisation (issue #89) : en haut de chaque onglet, une seule icône à côté du titre (Streamlit n'accepte
pas d'image dans le nom d'un onglet ; cisaillement : `cisaillement.svg`, compression perpendiculaire :
`compression_pres_appui.svg`), et dans la note PDF, à côté du titre de chaque vérification. La fonction
`icone_de_l_article()` de `moteur/commun/figures.py` choisit l'icône selon l'article et remplace les
couleurs de la marque par celles du compte. Grandes figures détaillées (variables du calcul, ex. longueur
d'appui) : `figure()` du même fichier.
