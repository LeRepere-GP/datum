# Icônes des degrés de retenue aux extrémités (tableau A.4) : proposition

Issue #90 et datum-retours #16 : choisir K_e de la compression parallèle au fil (6.5.5.1) avec une liste
d'icônes. Une icône par ligne du **tableau A.4** (annexe A, informative, CSA O86:19, p. 303-304), dans
l'ordre de la norme. Même style que les icônes des calculs (`marque/icones/`) : 64 x 64, au trait, sans
texte, couleur principale `#233614` (remplacée par celle du compte à l'affichage).

| Fichier | Degré de retenue aux extrémités (texte exact du tableau A.4) | K_e |
|---|---|---|
| `1_ke_0_65.svg` | Translation et rotation fixes aux deux extrémités | 0.65 |
| `2_ke_0_80.svg` | Translation fixe aux deux extrémités et rotation fixe à une extrémité | 0.80 |
| `3_ke_1_00.svg` | Translation fixe et rotation libre aux deux extrémités | 1.00 |
| `4_ke_1_20.svg` | Translation et rotation fixes à une extrémité, translation libre et rotation fixe à l'autre extrémité | 1.20 |
| `5_ke_1_50.svg` | Translation et rotation fixes à une extrémité, translation libre et rotation partiellement fixe à l'autre extrémité | 1.50 |
| `6_ke_2_00.svg` | Translation fixe et rotation libre à une extrémité, translation libre et rotation fixe à l'autre extrémité | 2.00 |
| `7_ke_2_00.svg` | Translation et rotation fixes à une extrémité, translation et rotation libres à l'autre extrémité | 2.00 |

Symboles :
- **Translation et rotation fixes** : plaque avec hachures (encastrement).
- **Translation fixe, rotation libre** : triangle sur une base hachurée (rotule).
- **Translation libre, rotation fixe** : plaque sur rouleaux (glissière) ; la déformée se déplace à
  l'horizontale et reste verticale à cette extrémité.
- **Rotation partiellement fixe** : la glissière, avec un triangle (rotule) entre l'élément et la plaque
  (demande de l'utilisateur, PR #92).
- **Translation et rotation libres** : aucun appui.
- **Déformée** (flambement) : trait pointillé, comme dans le tableau A.4.

Aperçu : `apercu.png`. Style validé (PR #92). Affichage : onglet Compression parallèle, une rangée par axe
(b et d) avec un bouton (K_e) sous chaque icône, plus « Autre » (K_e entré) ; fonction
`icones_des_degres_de_retenue()` de `moteur/commun/figures.py`.
