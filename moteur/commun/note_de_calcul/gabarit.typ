// Gabarit de la note de calcul PDF de Datum (ARCHITECTURE.md, section 8 ; issue #50, PR #55).
// Les données arrivent de Python (note_de_calcul/__init__.py) en JSON, par sys.inputs.donnees.
// Aucune logique de calcul ici : seulement la mise en page de la trace (Resultat).

#import "mitex/lib.typ": mitex, mi

#let donnees = json(bytes(sys.inputs.donnees))
#let entete = donnees.entete
#let apparence = donnees.apparence

// Couleurs : celles de la marque par défaut (marque/couleurs.md), ou celles de l'utilisateur
#let principale = rgb(apparence.principale)
#let accent = rgb(apparence.accent)
#let charbon = rgb("#333333")
#let gris = rgb("#8F8F8F")
#let gris-pale = rgb("#EEEEEE")
#let rouge = rgb("#A11D1D")

// Sans logo du compte : logo de Datum (symbole de Le Repère, sans le nom, et « Datum »)
#let logo(hauteur) = if apparence.logo == none {
  box(image("/marque/logos/LeRepere_symbole_gris.svg", height: hauteur), baseline: 25%)
  h(0.2cm)
  text(size: 16pt, weight: "bold", fill: principale)[Datum]
} else {
  image(bytes(apparence.logo), height: hauteur)
}

// Polices : celles du compte (ex. charte de Groupe Lantier), sinon celles de Typst par défaut
#let police-texte = if apparence.at("police_texte", default: none) == none { () } else { (apparence.police_texte,) }
#let police-titres = apparence.at("police_titres", default: none)
// Titre : police des titres en majuscules (charte du compte), sinon gras dans la police du texte
#let titre(taille, couleur, corps) = if police-titres == none {
  text(size: taille, fill: couleur, weight: "bold")[#corps]
} else {
  text(font: police-titres, size: taille * 1.15, fill: couleur, weight: "bold")[#upper(corps)]
}

#set document(title: "Note de calcul — " + entete.projet, author: entete.ingenieur)
#set text(lang: "fr", size: 9pt, fill: charbon, font: police-texte + ("Libertinus Serif",))
#set par(justify: false)

#let champ(nom, valeur) = [#text(fill: gris, size: 6.5pt)[#upper(nom)] \ #text(size: 8pt)[#valeur]]

// En-tête : logo et titre, puis les champs du dossier dans un bandeau gris pâle
#let en-tete = context {
  grid(
    columns: (1fr, auto),
    align: (left + horizon, right + horizon),
    logo(1.0cm),
    [
      #titre(12pt, principale, [Note de calcul]) \
      #text(size: 7pt, fill: gris)[Datum - Calculatrice Structurale]
    ],
  )
  v(0.2cm)
  block(width: 100%, fill: gris-pale, inset: (x: 6pt, y: 5pt), radius: 2pt, grid(
    columns: (1.1fr, 1.1fr, 1.4fr, 0.8fr),
    row-gutter: 0.18cm,
    column-gutter: 0.3cm,
    champ("Client", entete.client),
    champ("Projet", entete.projet),
    champ("Adresse du projet", entete.adresse),
    champ("N° de dossier", entete.dossier),
    champ("Norme et édition", entete.norme),
    champ("Ingénieur", entete.ingenieur + " — OIQ " + entete.oiq),
    champ("Date", entete.date),
    champ("Page", [#counter(page).display() de #counter(page).final().first()]),
  ))
  v(-0.1cm)
  line(length: 100%, stroke: 1.2pt + principale)
}

// Pied de page : zone d'initiales et de sceau en bas à droite, sur chaque page
#let pied = context grid(
  columns: (1fr, 4.2cm),
  align: (left + bottom, right + bottom),
  text(size: 7pt, fill: gris)[Note produite avec Datum - Calculatrice Structurale #donnees.version le #entete.date],
  rect(width: 4.2cm, height: 2.3cm, stroke: 0.6pt + gris, radius: 2pt)[
    #align(center + top)[#text(size: 6.5pt, fill: gris)[Initiales et sceau]]
  ],
)

// Marge du haut : l'en-tête commence à 1.2 cm du bord de la feuille
#set page(
  paper: "us-letter",
  margin: (top: 4.3cm, bottom: 3.3cm, x: 1.5cm),
  header: en-tete,
  header-ascent: 0.4cm,
  footer: pied,
  footer-descent: 0.3cm,
)

// Ordre des colonnes : symbole, valeur, description, source (demande de l'utilisateur, issue #62)
#let tableau-donnees(lignes) = table(
  columns: (auto, auto, 1fr, auto),
  stroke: none,
  inset: (x: 3pt, y: 2pt),
  fill: (_, y) => if y == 0 { principale } else if calc.even(y) { gris-pale },
  table.header(
    ..([Symbole], [Valeur], [Description], [Source]).map(t => text(fill: white, weight: "bold", size: 7.5pt)[#t]),
  ),
  ..lignes
    .map(l => (
      mi(l.symbole),
      text(size: 7.5pt)[#l.valeur],
      text(size: 7.5pt)[#l.description],
      text(size: 7pt, fill: accent)[#l.source],
    ))
    .flatten(),
)

// Une étape : calcul à gauche, résultat justifié à droite
#let etape(e) = block(breakable: false, above: 0.1cm, below: 0.1cm, width: 100%)[
  #text(fill: accent, weight: "bold", size: 7.5pt)[#e.article] #h(0.15cm) #text(size: 7.5pt)[#e.description]
  #v(-0.2cm)
  #show math.equation.where(block: true): set align(left)
  #set text(size: 8.5pt)
  #mitex(e.calcul)
  #v(-0.25cm)
  #align(right)[#mi(e.symbole) $=$ *#e.resultat*]
  #v(-0.1cm)
  #line(length: 100%, stroke: 0.3pt + gris-pale)
]

#let verification(v) = {
  let couleur = if v.respecte { principale } else { rouge }
  align(right, block(breakable: false, fill: couleur.lighten(88%), stroke: 1pt + couleur, inset: 7pt, radius: 3pt, width: 100%)[
    #set align(right)
    #text(weight: "bold", fill: couleur)[Vérification (#v.article)] \
    #mi(v.symbole_charge) $=$ #v.charge \
    #mi(v.symbole_resistance) $=$ #v.resistance \
    Ratio : *#v.ratio* — #text(weight: "bold", fill: couleur)[#v.message]
  ])
}

// Bloc de commentaires de l'ingénieur, lignes conservées : commentaires généraux (datum-retours #3)
// ou commentaire d'un calcul (datum-retours #21)
#let bloc-de-commentaires(texte, titre-du-bloc: [Commentaires]) = block(breakable: false, width: 100%, stroke: 0.6pt + gris, inset: 7pt, radius: 3pt)[
  #set align(left)
  #text(weight: "bold", fill: principale)[#titre-du-bloc] \
  #for (i, ligne) in texte.split("\n").enumerate() {
    if i > 0 { linebreak() }
    ligne
  }
]
#let commentaires = donnees.at("commentaires", default: "")
#let bloc-commentaires = bloc-de-commentaires(commentaires)

// Page résumé (issue #85) : une ligne par vérification faite, la vérification qui gouverne (ratio le
// plus élevé) en gras. Chaque titre renvoie à la page de sa vérification.
#let resume = donnees.at("resume", default: ())
#let page-de(indice) = context counter(page).at(label("verification-" + str(indice))).first()
#if resume.len() > 0 {
  block(below: 0.3cm, titre(11.5pt, principale, [Résumé des vérifications]))
  let cellule(l, corps) = text(size: 7.5pt, weight: if l.gouverne { "bold" } else { "regular" })[#corps]
  table(
    columns: (1fr, auto, auto, auto, auto, auto),
    stroke: none,
    inset: (x: 3pt, y: 3pt),
    align: (left + horizon, left + horizon, left + horizon, left + horizon, right + horizon, left + horizon),
    fill: (_, y) => if y == 0 { principale } else if calc.even(y) { gris-pale },
    table.header(
      ..([Vérification], [Article], [Charge pondérée], [Résistance pondérée], [Ratio], [Statut])
        .map(t => text(fill: white, weight: "bold", size: 7.5pt)[#t]),
    ),
    ..resume
      .map(l => {
        let couleur = if l.respecte { principale } else { rouge }
        (
          cellule(l, link(label("verification-" + str(l.indice)))[
            #l.titre #if l.element != "" [— #l.element] #text(fill: gris)[(p. #page-de(l.indice))]
          ]),
          text(size: 7.5pt, fill: accent, weight: "bold")[#l.article],
          cellule(l, [#mi(l.symbole_charge) $=$ #l.charge]),
          cellule(l, [#mi(l.symbole_resistance) $=$ #l.resistance]),
          cellule(l, l.ratio),
          text(size: 7.5pt, weight: "bold", fill: couleur)[#if l.respecte [✔] else [✖] #l.statut],
        )
      })
      .flatten(),
  )
  text(size: 7pt, fill: gris)[En gras : la vérification qui gouverne (ratio le plus élevé).]
  // Commentaires de l'ingénieur sur la page résumé seulement (décision de l'utilisateur, PR #93), en bas
  // à gauche, à côté du sceau
  if commentaires != "" {
    place(bottom, float: true, clearance: 0.3cm, grid(columns: (1fr, 1fr), column-gutter: 0.6cm, bloc-commentaires))
  }
  pagebreak()
}

#for (i, r) in donnees.resultats.enumerate() {
  if i > 0 { pagebreak() }
  // Repère de la page de cette vérification, pour les renvois de la page résumé (issue #85)
  [#metadata(i) #label("verification-" + str(i))]
  block(below: 0.2cm)[
    // Petite icône du type de calcul à côté du titre (issue #89)
    #if r.icone_svg != none {
      box(baseline: 25%, image(bytes(r.icone_svg), format: "svg", height: 0.8cm))
      h(0.2cm)
    }
    #titre(11.5pt, principale, [#r.titre #if r.element != "" [— #r.element]])
    #h(1fr) #text(size: 8.5pt, fill: accent, weight: "bold")[#r.norme, article #r.article]
  ]

  if r.en_test {
    block(width: 100%, fill: rgb("#FFF4D6"), stroke: 0.8pt + rgb("#B07A00"), inset: 5pt, radius: 2pt, below: 0.2cm)[
      #text(size: 8pt, fill: rgb("#7A5200"), weight: "bold")[En test :]
      #text(size: 8pt, fill: rgb("#7A5200"))[vérifiez les résultats avant de les utiliser dans un dossier.]
    ]
  }
  grid(
    columns: (6cm, 1fr),
    column-gutter: 0.35cm,
    // Figure schématique de la vérification (issue #62), sinon un encadré « à venir »
    if r.figure_svg != none {
      align(center + horizon, image(bytes(r.figure_svg), format: "svg", width: 100%))
    } else {
      rect(width: 100%, height: 3.4cm, stroke: (dash: "dashed", paint: gris, thickness: 0.6pt), radius: 2pt)[
        #align(center + horizon)[#text(fill: gris, size: 7pt)[Figure schématique \ (à venir) \ #r.figure]]
      ]
    },
    tableau-donnees(r.donnees),
  )

  v(0.15cm)
  titre(9.5pt, principale, [Calcul])
  // Vérification ancrée en bas à droite, juste au-dessus du sceau (revue de la PR #55). Placée avant
  // les étapes pour réserver l'espace : les calculs ne passent jamais dessous.
  // Commentaires de l'ingénieur en bas à gauche de la première page, à côté de la vérification et
  // du sceau (datum-retours #3) : la note tient le plus possible sur une seule page.
  // S'il y a une page résumé, les commentaires y sont déjà (PR #93) : pas sur la page de vérification.
  let avec-commentaires = i == 0 and commentaires != "" and resume.len() == 0
  // Commentaire de l'ingénieur sur ce calcul (datum-retours #21) : à la fin de la page de cette
  // vérification, dans la même colonne que les commentaires généraux (sous ceux-ci s'il y en a).
  let commentaire = r.at("commentaire", default: "")
  let avec-commentaire = commentaire != ""
  if r.verification != none or avec-commentaires or avec-commentaire {
    place(bottom, float: true, clearance: 0.3cm, grid(
      columns: (1fr, 1fr),
      column-gutter: 0.6cm,
      align: bottom,
      stack(
        spacing: 0.2cm,
        ..if avec-commentaires { (bloc-commentaires,) } else { () },
        ..if avec-commentaire {
          // Titre distinct si les commentaires généraux sont sur la même page, pour les différencier
          let titre-du-bloc = if avec-commentaires [Commentaires sur ce calcul] else [Commentaires]
          (bloc-de-commentaires(commentaire, titre-du-bloc: titre-du-bloc),)
        } else { () },
      ),
      if r.verification != none { verification(r.verification) },
    ))
  }
  // Notes de la norme, à la suite des étapes dans les mêmes colonnes (ex. exigences d'assemblage de
  // 6.5.5.4 que Datum ne vérifie pas, issue #32) : une puce par note
  let notes = r.at("notes", default: ())
  columns(2, gutter: 0.6cm)[
    #for e in r.etapes { etape(e) }
    #if notes.len() > 0 {
      v(0.1cm)
      titre(9.5pt, principale, [Notes])
      set text(size: 7.5pt)
      list(..notes.map(n => [#n]))
    }
  ]
}
