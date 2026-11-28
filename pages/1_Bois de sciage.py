"""Page Streamlit : calcul des éléments en bois de sciage (CSA O86:19, chapitre 6)."""

# IMPORTS
import streamlit as st
import acces
import config
import interface_unites as iu
import datetime
from moteur.commun.nombres import cs
from moteur.commun.figures import (
    figure,
    figure_avant_le_calcul,
    icone_de_l_article,
    icones_des_degres_de_retenue,
    largeur_de_la_vue,
    section_de_l_element,
)
from moteur.commun.note_de_calcul import (
    EnTete,
    formater_ligne_du_resume,
    nom_du_pdf,
    produire_pdf,
)
from moteur.commun.piece import lire_piece
from moteur.commun.resume import (
    CHARGE_MANQUANTE,
    CONFORME,
    NON_CALCULE,
    NON_CONFORME,
    VerificationPrevue,
    resume_des_verifications_offertes,
)
from moteur.normes.csa_o86_19.ch_5_conception_generale import (
    art_5_3_conditions_et_coefficients_influant_sur_la_resistance as art_5_3,
)
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage import art_6_2_materiaux as art_6_2
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_3_resistances_prevues_et_modules_d_elasticite import (  # noqa: E501
    tableau_des_resistances,
)
from moteur.normes.csa_o86_19.ch_6_bois_de_sciage.art_6_5_calcul_des_resistances import (
    art_6_5_3_resistance_au_moment_de_flexion as art_6_5_3,
    art_6_5_4_resistance_au_cisaillement as art_6_5_4,
    art_6_5_5_resistance_a_la_compression_parallele_au_fil as art_6_5_5,
    art_6_5_6_resistance_a_la_compression_perpendiculaire_au_fil as art_6_5_6,
)
from moteur.normes.csa_o86_19.annexe_A_renseignements_supplementaires_et_autres_methodes.art_A_6_bois_de_sciage import (  # noqa: E501
    art_A_6_5_5_1_coefficient_de_longueur_effective as art_A_6_5_5_1,
    art_A_6_5_6_compression_perpendiculaire_au_fil as art_A_6_5_6,
)
from moteur.normes.csa_o86_19.annexe_A_renseignements_supplementaires_et_autres_methodes.tableaux import (  # noqa: E501
    tableau_A_3_dimensions_minimales_apres_rabotage_du_bois_d_oeuvre as tableau_A_3,
    tableau_A_11_valeurs_de_densite as tableau_A_11,
)
import sawn_lumber
import general_design
from sawn_lumber import SawnLumberStrengths


# CODE
def show_verification(message: str) -> None:
    """Affiche le résultat de la vérification à l'état limite avec la bonne couleur."""
    if message.startswith("État limite respecté"):
        st.success(message, width=650, icon=":material/check_circle:")
    elif message.startswith("État limite dépassé"):
        st.error(message, width=650, icon=":material/error:")
    else:
        st.info(message, width=650, icon=":material/info:")


def afficher_resistance_et_verification(resultat, symbole: str) -> None:
    """
    Affiche la résistance pondérée (en N dans la trace, affichée en kN) et la vérification, tirées de la
    trace du nouveau moteur (issue #98). Mêmes chiffres significatifs que le Résumé et la note PDF.
    """
    etape = resultat.etape(symbole)
    assert etape.unite == "N", f"{symbole} : unité {etape.unite!r} inattendue (N attendu)"
    st.write(f"${symbole} = {iu.latex_significatif(etape.valeur / 1000, 'force')}$")
    if resultat.verification is None:
        show_verification(general_design.limit_states_design(None, etape.valeur))
    else:
        show_verification(resultat.verification.message())


def valeur_de_l_etape(etape) -> str:
    """
    Résultat d'une étape de la trace pour l'affichage (« Voir plus ») : les forces sont en N dans la trace
    et affichées en kN, avec l'impérial ; les autres valeurs avec leur grandeur, ou sans unité.
    """
    if etape.unite == "N":
        return iu.latex_significatif(etape.valeur / 1000, "force")  # N / 1000 = kN
    if etape.grandeur is not None:
        return iu.latex_significatif(etape.valeur, etape.grandeur)
    return f"{cs(etape.valeur)} {etape.unite}".strip()


# ---- en-tête ----
config.configurer_page("Bois de sciage")
EDITION = config.choisir_edition()  # une seule pour l'instant : CSA O86:19 (issue #72)
# Unités (retour #10, PR #99) : saisie libre dans chaque champ (ex. 8 pi 38 mm, 5 kN, 1124 lb) ;
# unité par défaut des nombres sans unité dans la barre latérale ; résultats dans les deux unités.
# Les calculs restent en métrique.
iu.choisir_systemes()
st.title(config.TITLE, anchor=False)
st.caption(config.SOUS_TITRE)
st.header(
    "Bois de Sciage",
    anchor=False,
    help="""Les méthodes et les données de calcul ne s'appliquent qu'au bois de charpente
    conforme à CSA O141""",
)


# --- en-tête de la note de calcul (datum-retours #21) ---
# L'en-tête de la note (client, projet, adresse, dossier, date, ingénieur, OIQ, titre) est en haut de
# la page, pour être rempli en premier, dans une section qu'on peut replier une fois remplie. Ici, on
# réserve seulement sa place : les champs sont créés plus bas (section « Note de calcul »), parce que
# le titre par défaut dépend de la pièce choisie dans « Matériaux », qui n'est pas encore lue ici.
# Streamlit affiche les champs à la place réservée, même s'ils sont créés plus loin dans le script.
EN_TETE_DE_LA_NOTE = None
if acces.permis("note_pdf"):
    with st.container(horizontal_alignment="center"):
        EN_TETE_DE_LA_NOTE = st.expander(
            "En-tête de la note de calcul", expanded=True, icon=":material/description:", width=650
        )

# --- section matériaux ---
st.divider()
st.subheader(
    "Matériaux",
    anchor=False,
    help=""" Les calculs reposent sur l'utilisation de bois d'œuvre classé suivant les Règles
    de classification pour le bois d'œuvre canadien de la NLGA, et identifié au moyen de 
    l'estampille d'une association ou d'un organisme indépendant de classement, conformément 
    à CSA O141""",
)

with st.container(horizontal_alignment="center"):
    # --- inputs pour déterminer la catégorie ---
    col1, col2 = st.columns(
        2,
        gap="medium",
        width=550,
    )

    with col1:
        # Pièce en texte libre (datum-retours #20) : une seule boîte remplace les anciens champs (bois vert,
        # dimensions brutes, largeur, hauteur et nombre de plis ; retirés, décision de l'utilisateur).
        # Lecture du texte : moteur/commun/piece.py ; dimensions nettes : tableau A.3
        # (dimensions_de_la_piece()). Aucune logique de calcul ici.
        texte_de_la_piece = st.text_input(
            "Pièce",
            value="2x6",
            key="piece",
            icon=":material/straighten:",
            help="""Plis (facultatif), largeur x hauteur, puis « vert » ou « brut » au besoin.
            Ex. : 2x10 ; 2 2x6 ou 2-2x6 (2 plis) ; 4x4 vert ; 5 1/4 x 8 7/16 ; 2x6 brut ; 89 x 140 mm.
            Dimensions entières du tableau A.3 : nominales. Dimensions non entières ou absentes du
            tableau A.3 : brutes. En mm : dimensions réelles. Plis : de 1 à 5.""",
        )
        try:
            DIMENSIONS = tableau_A_3.dimensions_de_la_piece(lire_piece(texte_de_la_piece))
        except ValueError as error:
            # Texte refusé : message avec la raison, et rien n'est calculé (jamais de valeur devinée)
            st.error(f"« {texte_de_la_piece} » : {error}.", icon=":material/error:")
            st.stop()
        # Ce que Datum a compris, toujours affiché sous la boîte (décision de l'utilisateur, #20)
        st.caption(
            f"Compris : {DIMENSIONS.description()} : "
            + (
                f"b = {DIMENSIONS.nombre_de_plis} × {iu.texte(DIMENSIONS.largeur_d_un_pli, 'dimension')} "
                f"= {iu.texte(DIMENSIONS.b, 'dimension')}"
                if DIMENSIONS.nombre_de_plis > 1
                else f"b = {iu.texte(DIMENSIONS.b, 'dimension')}"
            )
            + f", d = {iu.texte(DIMENSIONS.d, 'dimension')}."
        )
        # Mêmes noms qu'avant pour la suite de la page : width = largeur nette d'un pli (mm), depth = d (mm),
        # built_up = nombre de plis
        width, depth, built_up = DIMENSIONS.largeur_d_un_pli, DIMENSIONS.d, DIMENSIONS.nombre_de_plis

    with col2:
        if built_up == 1:
            st.metric("Largeur nette de l'élément, $b$", iu.texte(width, "dimension"))
        else:
            st.metric(
                "Largeur nette de l'élément, $b$",
                f"{built_up}*{width:g} = {iu.texte(built_up * width, 'dimension')}",
            )

        st.metric("Hauteur nette de l'élément, $d$", iu.texte(depth, "dimension"))
        # Section de l'élément (b, d et les plis), affichée ici une seule fois plutôt que dans chaque
        # onglet de calcul (retour #12) ; même échelle que les figures des onglets
        apparence_du_compte = config.apparence_du_compte(st.session_state.get("compte", ""))
        svg_de_la_section = section_de_l_element(
            built_up, apparence_du_compte.principale, apparence_du_compte.accent
        )
        st.image(svg_de_la_section, width=round(440 * largeur_de_la_vue(svg_de_la_section) / 360))
        msr_mel = col2.segmented_control(
            label="Bois classé mécaniquement?",
            options=("MSR", "MEL"),
            width="stretch",
            help="""Bois de charpente classé mécaniquement par résistance (MSR) et
            bois de charpente évalué par machine (MEL)""",
        )
        MSR, MEL = False, False
        if msr_mel == "MSR":
            MSR = True
        elif msr_mel == "MEL":
            MEL = True
        LIGHT_FRAMING = False
        if not (MSR or MEL) and art_6_2.admet_charpente_legere(width, depth):
            LIGHT_FRAMING = col2.toggle(
                "Charpente légère (Const., Std.)",
                help="""Tableau 6.3 : une section de 38 à 89 mm x 38 à 89 mm peut prendre les classes
                du tableau 6.4 (structure choisie, n° 1/n° 2, n° 3/montant), utilisées par défaut, ou
                celles du tableau 6.5 (Construction, Standard).""",
            )

    # --- calcul pour déterminer la catégorie (6.2.2, tableau 6.3) ---
    # Grande face de plus de 412 mm : avertissement, puis catégorie « Beam » (comportement conservé)
    try:
        CATEGORY = art_6_2.categorie_de_bois(
            width, depth, msr=MSR, mel=MEL, charpente_legere=LIGHT_FRAMING
        )
    except ValueError as error:
        if min(width, depth) < 38 or max(width, depth) <= art_6_2.DIMENSION_MAXIMALE:
            st.error(str(error), icon=":material/error:")
            st.stop()
        col1.warning(str(error), width=550, icon=":material/person_alert:")
        CATEGORY = "Beam"
        MSR, MEL = False, False

    # --- afficher le résultat de la catégorie ---
    with col2.expander("Catégorie", expanded=True):
        category = {
            "Light": "Charpente légère",
            "Beam": "Poutres et longerons",
            "Post": "Poteaux et bois carrés",
            "Lumber": "Montants, solives et madriers",
            "MEL": "MEL",
            "MSR": "MSR",
        }
        st.text(category[CATEGORY])

    # --- inputs pour déterminer les résistances prévues ---
    SIDE = False
    if CATEGORY == "Beam":
        SIDE = st.toggle(
            "Charges appliquées sur la grande face",
            help="""
            Les résistances prévues des poutres et des longerons sont fondées sur des charges
            appliquées sur leur face étroite. Si les charges sont appliquées sur leur grande face,
            la résistance prévue en flexion à la fibre extrême et le module d'élasticité prévu 
            doivent être multipliés par des coefficients de correction (CSA O86 - Tableau 6.6)
            """,
            width=550,
        )

    # --- choix de la classe ou essence de bois ---
    if MSR or MEL:
        st.caption(
            """Le groupe d'essences S-P-F est utilisé par défaut pour caractériser le bois classé 
            mécaniquement""",
            width=550,
        )
    specie = {
        "Courant": "courant",
        "Normal": "normal",
        "Rare": "rare",
        "D Fir-L (N)": "df",
        "Hem-Fir (N)": "hf",
        "S-P-F": "spf",
        "N. Species": "ns",
    }
    if MSR:
        SPECIE = st.segmented_control(
            label="Groupe:",
            options=("Courant", "Normal", "Rare"),
            default="Courant",
            width=650,
            help="Si aucun Groupe n'est sélectionné, 'Courant' est utilisé par défaut",
        )
        if not SPECIE:
            SPECIE = "Courant"
    elif MEL:
        SPECIE = "Normal"
    else:
        SPECIE = st.segmented_control(
            label="Groupe d'essences:",
            options=("D Fir-L (N)", "Hem-Fir (N)", "S-P-F", "N. Species"),
            default="S-P-F",
            width=650,
            help="Si aucune essence n'est sélectionnée, le groupe 'S-P-F' est utilisé par défaut",
        )
        if not SPECIE:
            SPECIE = "S-P-F"

    # --- choix du grade ---
    grade_options = (
        SawnLumberStrengths.session.query(SawnLumberStrengths)  # type: ignore
        .filter(SawnLumberStrengths.category == CATEGORY)  # type: ignore
        .filter(SawnLumberStrengths.specie == specie[SPECIE])  # type: ignore
        .with_entities(SawnLumberStrengths.grade)  # type: ignore
    )
    grade = st.segmented_control(
        label="Classe:",
        options=grade_options,
        default=grade_options[1][0],
        width=650,
        help=f"Si aucune classe n'est sélectionnée, '{grade_options[1][0]}' est utilisé par défaut",
    )
    if not grade:
        grade = grade_options[1][0]


# --- section résistances prévues ---
st.divider()
st.subheader("Résistances prévues et modules d'élasticité", anchor=False)

# --- calculer les résultats de résistances prévues ---
compute_resistance = sawn_lumber.specified_strengths(
    category=CATEGORY,
    specie=specie[SPECIE],
    grade=grade,
    side=SIDE,
)

with st.container(horizontal_alignment="center"):
    # --- afficher les résultats de résistances prévues ---
    with st.expander("Voir plus:", width=650):
        display_resistance = [
            (
                "Flexion",
                "$f_b$",
            ),
            (
                "Cisaillement longitudinal",
                "$f_v$",
            ),
            (
                "Compression parallèle au fil",
                "$f_c$",
            ),
            (
                "Compression perpendiculaire au fil",
                "$f_{cp}$",
            ),
            (
                "Traction parallèle au fil",
                "$f_t$",
            ),
            (
                "Module d'élasticité",
                "$E$",
            ),
            (
                "Module d'élasticité pour les calculs des éléments en compression",
                "$E_{05}$",
            ),
        ]
        for i in range(0, int(len(compute_resistance))):
            col1, col2 = st.columns([3, 1])
            col1.text(f"{display_resistance[i][0]}:")
            col2.markdown(
                f"{display_resistance[i][1]} $= {iu.latex(compute_resistance[i], 'contrainte')}$"
            )


# --- section coefficients ---
st.divider()
st.subheader("Coefficients de correction", anchor=False)

with st.container(horizontal_alignment="center"):
    # --- inputs pour déterminer les coefficients ---
    col1, col2 = st.columns(2, vertical_alignment="bottom", width=550)
    duration = {
        "Courte (≤ 7 jours)": "courte",
        "Normale": "normale",
        "Continue (permanente)": "continue",
    }
    DURATION = col1.radio(
        label="Durée d'application de la charge:",
        options=("Courte (≤ 7 jours)", "Normale", "Continue (permanente)"),
        index=1,
        horizontal=False,
    )
    wet = col1.checkbox(
        "Utilisation en milieu humide",
    )
    treated = col2.checkbox(
        "Bois traité",
        help="""Dans le cas du bois d'œuvre traité par ignifugation ou avec d'autres produits
        chimiques qui réduisent la résistance, les résistances et la rigidité doivent être
        basées sur des résultats d'essais documentés qui doivent tenir compte de l'effet du
        temps, de la température et de la teneur en humidité""",
    )
    incised = col2.checkbox(
        "Bois incisé",
    )
    group = col2.checkbox(
        "3 éléments ou + @ ≤ 2 pi c/c",
        help="""Cas 1 - Système d'éléments de charpente rapprochés comme les
        fermes à ossature légère, les éléments de charpente composés et les éléments de
        charpente en bois lamellé-collé. Peut aussi s'appliquer à certains systèmes
        traditionnels de solives et de chevrons où les détails de charpente ne satisfont pas
        au cas 2""",
    )
    subfloor = col2.checkbox(
        "Revêtement ou sous-plancher",
        help="""Cas 2 - Système d'éléments revêtus d'un contreplaqué ou d'un panneau OSB d'au
        moins 9,5 mm d'épaisseur, ou de bois d'au moins 17 mm d'épaisseur combiné à un
        recouvrement de panneaux tel qu'une sous-finition ou un parquet de bois. Le revêtement
        ou le sous-plancher est fixé aux éléments de charpente de manière à procurer une
        rigidité minimale équivalente à celle obtenue à l'aide de clous ordinaires de 2 po
        espacés de 150 mm aux rives des panneaux de revêtement et de 300 mm aux autres
        endroits""",
    )
    # K_D par les charges (5.3.2.2, issue #58) : en option, pour une durée continue
    CHARGES = None  # None : K_D du tableau 5.1
    SOURCE_KD = "Tableau 5.1"
    if duration[DURATION] == "continue":
        with st.container(width=550):
            if st.checkbox(
                "Calculer $K_D$ à partir des charges (5.3.2.2)",
                key="kd_charges",
                help="""Si la charge spécifiée de durée continue, P_L, est plus grande que la charge
                spécifiée de durée normale, P_s, K_D = 1.0 - 0.50 log(P_L / P_s) >= 0.65, où
                P_s = max(S ; L ; S + 0.5 L ; 0.5 S + L). Sans charges : K_D = 0.65 (tableau 5.1).""",
            ):
                AIDE_UNITE = """Toute unité cohérente convient pour les trois charges (ex. kN/m) :
                seul le rapport P_L / P_s compte."""
                c1, c2, c3 = st.columns(3)
                # Seul le rapport P_L / P_s compte : aucune conversion, l'unité n'est qu'un repère
                PRESSION = iu.unite("pression")
                p_l = c1.number_input(
                    f"$P_L$ ({PRESSION})", min_value=0.0, value=None, key="kd_p_l",
                    help="Charge spécifiée de durée d'application continue (ex. charge permanente). "
                    + AIDE_UNITE,
                )
                neige = c2.number_input(
                    f"$S$ ({PRESSION})", min_value=0.0, value=None, key="kd_s",
                    help="Charge de neige spécifiée. " + AIDE_UNITE,
                )
                surcharge = c3.number_input(
                    f"$L$ ({PRESSION})", min_value=0.0, value=None, key="kd_l",
                    help="Surcharge spécifiée. " + AIDE_UNITE,
                )
                if p_l is None or not (neige or surcharge):
                    st.info(
                        "Entrez $P_L$ et au moins $S$ ou $L$. En attendant : $K_D$ = 0.65 "
                        "(tableau 5.1).",
                        icon=":material/info:",
                    )
                else:
                    CHARGES = {"dead": p_l, "snow": neige or 0.0, "live": surcharge or 0.0}
                    SOURCE_KD = "5.3.2.2"
                    p_s = art_5_3.P_s(CHARGES["snow"], CHARGES["live"])
                    kd_charges = general_design.load_duration("continue", **CHARGES)
                    st.write(f"$P_s = {p_s:.2f}$ {PRESSION} ; $K_D = {kd_charges:.3f}$")
                    if p_l <= p_s:
                        st.warning(
                            "$P_L \\leq P_s$ : la charge de durée continue ne domine pas. "
                            "$K_D$ = 1.00 (5.3.2.2 ne s'applique pas) ; la durée normale convient.",
                            icon=":material/warning:",
                        )

    PLIS = True
    if built_up == 1:
        PLIS = False

    # --- afficher les résultats des coefficients ---
    with st.expander("Voir plus:", width=650):
        prop_options = {
            "Flexion": "flex",
            "Cisaillement par fissuration": "cis_f",
            "Cisaillement longitudinal": "cis_v",
            "Compression parallèle au fil": "comp_para",
            "Compression perpendiculaire au fil": "comp_perp",
            "Traction parallèle au fil": "trac",
            "Module d'élasticité": "moe",
        }
        PROP_KEY = st.segmented_control(
            """Pour consultation uniquement, les bons coefficients sont utilisés automatiquement
            dans les calculs""",
            options=prop_options,
            width="stretch",
            default="Flexion",
            help="Si aucune propriété n'est sélectionné, 'Flexion' est sélectionné par défaut",
        )
        if not PROP_KEY:
            PROP_KEY = "Flexion"

        # --- calculer les corfficients ---
        compute_coefficients = sawn_lumber.modification_factors(
            width=width,
            depth=depth,
            prop=prop_options[PROP_KEY],
            duration=duration[DURATION],
            loads=CHARGES,
            category=CATEGORY,
            wet_service=wet,
            treated=treated,
            incised=incised,
            _2ft_spacing=group,
            connected_subfloor=subfloor,
            built_up_beam=PLIS,
        )

        display_coefficients = [
            ("Coefficient de durée d'application de la charge", "$K_D$"),
            ("Coefficient de conditions d'utilisation", "$K_S$"),
            ("Coefficient de traitement", "$K_T$"),
            ("Coefficient de système", "$K_H$"),
            ("Coefficient de dimensions", "$K_Z$"),
        ]
        for i in range(0, int(len(compute_coefficients))):
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"{display_coefficients[i][0]}:")
            col2.markdown(f"{display_coefficients[i][1]} $={compute_coefficients[i]}$")


# --- section calcul des résistances ---
st.divider()
st.subheader("Calcul des résistances", anchor=False)
# Vérifications pour la note de calcul PDF (issue #50) : traces du nouveau moteur, mêmes entrées
NOTE = {}
SOURCE = tableau_des_resistances(CATEGORY)  # tableau des résistances prévues (6.3)


def afficher_figures(*noms: str, echelle: float = 440 / 360) -> None:
    """
    Figures schématiques des vérifications (issue #62), dans les couleurs du compte. La figure est
    affichée dès l'ouverture de l'onglet, avant d'entrer les valeurs (retours #9, #13 et #14) : elle
    ne montre que des symboles. L'article est entre parenthèses à la fin du nom (ex. « (6.5.3) »).

    La section de l'élément (b, d) n'est pas répétée dans chaque onglet : elle est dans « Matériaux »
    (retour #12). Les figures de 6.5.6 la gardent, avec la largeur d'appui b. Toutes les figures sont
    à la même échelle (pixels par unité du SVG), pour que le texte ait la même taille.
    """
    apparence = config.apparence_du_compte(st.session_state.get("compte", ""))
    for nom in noms:
        if nom in NOTE:
            svg = figure(NOTE[nom], apparence.principale, apparence.accent, avec_section=False)
        else:
            article = nom.rsplit("(", 1)[-1].rstrip(")")
            svg = figure_avant_le_calcul(
                article, built_up, apparence.principale, apparence.accent, avec_section=False
            )
        if svg:
            st.image(svg, width=round(echelle * largeur_de_la_vue(svg)))


def afficher_titre_de_l_onglet(titre: str, article: str) -> None:
    """
    Titre d'un onglet, précédé d'une seule petite icône (issue #89, retour de la PR #91), dans les
    couleurs du compte. Streamlit n'accepte pas d'image dans le nom d'un onglet : l'icône va en haut
    de l'onglet. Un article sans icône (ex. compression oblique) n'en affiche pas.
    """
    apparence = config.apparence_du_compte(st.session_state.get("compte", ""))
    svg = icone_de_l_article(article, apparence.principale, apparence.accent)
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        if svg:
            st.image(svg, width=44)
        st.markdown(f"**{titre}**")


def _choisir(cle: str, valeur: int | None) -> None:
    st.session_state[cle] = valeur


def choisir_les_degres_de_retenue() -> dict[str, str | None]:
    """
    Choix du degré de retenue aux extrémités pour le flambage selon b et selon d (tableau A.4, annexe A
    informative, p. 303-304 ; issue #90) : une rangée des 7 icônes du tableau, avec un bouton sous
    chacune (son K_e), et « Autre » pour entrer K_e. Streamlit n'accepte pas d'image dans une liste.
    Par défaut : translation fixe et rotation libre aux deux extrémités (K_e = 1.00).

    Returns:
        dict[str, str | None]: Degré de retenue choisi pour chaque axe ("b", "d"), texte exact du
            tableau A.4 ; None pour « Autre » (K_e entré par l'utilisateur).
    """
    degres = art_A_6_5_5_1.degres_de_retenue()
    apparence = config.apparence_du_compte(st.session_state.get("compte", ""))
    icones = icones_des_degres_de_retenue(apparence.principale, apparence.accent)
    par_defaut = degres.index("Translation fixe et rotation libre aux deux extrémités")
    choix = {}
    for axe, nom in (("b", "largeur"), ("d", "hauteur")):
        cle = f"cpa_degre_selon_{axe}"
        st.session_state.setdefault(cle, par_defaut)
        st.markdown(f"Conditions d'appui, flambage selon la {nom} ${axe}$ (tableau A.4)", width=650)
        # Une case par icône (icône centrée au-dessus de son bouton) ; les cases passent à la ligne sur
        # un écran étroit (cellulaire), au lieu de s'empiler en colonne comme st.columns
        with st.container(horizontal=True, wrap=True, gap="small", width=650):
            for i, (degre, svg) in enumerate(zip(degres, icones)):
                with st.container(width=68, horizontal_alignment="center", gap="small"):
                    st.image(svg, width=56)
                    st.button(
                        f"{art_A_6_5_5_1.K_e(degre):.2f}",
                        key=f"{cle}_{i}",
                        help=degre,
                        type="primary" if st.session_state[cle] == i else "secondary",
                        on_click=_choisir,
                        args=(cle, i),
                        width="stretch",
                    )
            with st.container(width=68, height="stretch", vertical_alignment="bottom"):
                st.button(
                    "Autre",
                    key=f"{cle}_autre",
                    help="Entrer $K_e$",
                    type="primary" if st.session_state[cle] is None else "secondary",
                    on_click=_choisir,
                    args=(cle, None),
                    width="stretch",
                )
        choix[axe] = None if st.session_state[cle] is None else degres[st.session_state[cle]]
    return choix


def source_du_K_e(degre_de_retenue: str | None) -> str:
    """Source de K_e pour la note de calcul (issue #90) : tableau A.4, ou None pour « Autre »."""
    return "Tableau A.4" if degre_de_retenue is not None else "Entré par l'utilisateur"


# Onglets offerts au compte connecté (acces.py, ACCES_GROUPE_LANTIER.md ; issue #56)
ONGLETS_POSSIBLES = {
    "flexion": "Moment de flexion",
    "cisaillement": "Cisaillement",
    "compression_parallele": "Compression parallèle au fil",
    "compression_perpendiculaire": "Compression perpendiculaire au fil",
    "compression_oblique": "Compression oblique par rapport au fil",
    "traction": "Traction parallèle au fil",
    "flexion_et_charge_axiale": "Flexion et charge axiale combinée",
}
OFFERTS = [cle for cle in ONGLETS_POSSIBLES if acces.permis(cle)]
ONGLETS = dict(zip(OFFERTS, st.tabs([ONGLETS_POSSIBLES[cle] for cle in OFFERTS]))) if OFFERTS else {}
if not OFFERTS:
    st.info(
        "Aucune vérification n'est encore offerte à ce compte.", width=650, icon=":material/info:"
    )

if "flexion" in ONGLETS:
    with ONGLETS["flexion"]:
        afficher_titre_de_l_onglet("Moment de flexion (6.5.3)", "6.5.3")
        acces.avertir_si_en_test("flexion")
        kd, ksb, kt, kh, kzb = sawn_lumber.modification_factors(
            width=width,
            depth=depth,
            prop="flex",
            duration=duration[DURATION],
            loads=CHARGES,
            category=CATEGORY,
            wet_service=wet,
            treated=treated,
            incised=incised,
            _2ft_spacing=group,
            connected_subfloor=subfloor,
            built_up_beam=PLIS,
        )
        beam_flex = sawn_lumber.Resistances(
            b=width,
            d=depth,
            kd=kd,
            kh=kh,
            kt=kt,
            ply=built_up,
        )

        with st.container(horizontal_alignment="center"):
            col1, col2 = st.columns(2, width=550)
            with col1:
                LATERAL = st.toggle(
                    "Support latéral aux appuis",
                    help="""Support latéral assuré aux points d'appui afin d'empêcher le déplacement
                    latéral et la rotation""",
                    value=True,
                )
                TIE_ROD = st.toggle(
                    "Pannes ou tirants",
                    help="Alignement maintenu à l'aide de pannes ou de tirants",
                )
                COMP_EDGE = st.toggle(
                    "Rive supérieure maintenue",
                    help="""Rive comprimée maintenu par fixation directe du platelage ou par des solives
                    dont l'espacement ne dépasse pas """ + iu.texte(610, "dimension"),
                    value=subfloor,
                )
                BLOCK = st.toggle(
                    "Entremises",
                    help=f"""Présence d'entretoises ou d'entremises dont l'espacement ne dépasse pas
                    huit fois la hauteur de la section de l'élément -> $8 \\cdot d =$
                    {iu.texte(8 * depth, "dimension")} c/c""",
                )
                TEN_EDGE = st.toggle(
                    "Rive inférieure maintenue",
                    help="Rive en tension maintenue",
                )
                PLIES_FASTENED = False
                if built_up > 1:
                    PLIES_FASTENED = st.toggle(
                        f"Plis fixés à au plus 4d = "
                        f"{iu.texte(4 * depth, 'dimension')} c/c",
                        help="""6.5.3.2.4 : poutre composée dont les plis sont solidement attachés les
                        uns aux autres à intervalles ne dépassant pas quatre fois la hauteur. Les
                        supports latéraux ci-dessus (6.5.3.2.3) ne s'appliquent pas aux poutres
                        composées.""",
                    )

            try:
                mr = (
                    beam_flex.bending_moment(
                        fb=compute_resistance[0],
                        ksb=ksb,
                        kzb=kzb,
                        lateral_support=LATERAL,
                        compressive_edge_support=COMP_EDGE,
                        tensile_edge_support=TEN_EDGE,
                        blocking_support=BLOCK,
                        tie_rods_support=TIE_ROD,
                        plies_fastened=PLIES_FASTENED,
                    )
                    / 1000000
                )
            except ValueError as error:
                mr = None
                kl_message = str(error)
            with col2:
                mf = iu.champ(
                    "$M_f: ({unite})$",
                    "moment",
                    key="flex_mf",
                    min_value=0.0,
                    width=550,
                    placeholder="Moment pondéré",
                    icon=":material/input:",
                )
                if mr is None:
                    st.error(kl_message, width=650, icon=":material/error:")
                else:
                    VERIF = general_design.limit_states_design(mf, mr)
                    st.write(f"$M_r = {iu.latex_significatif(mr, 'moment')}$")
                    show_verification(VERIF)
                    NOTE["Flexion (6.5.3)"] = art_6_5_3.verifier_flexion(
                        b=width * built_up, d=depth, f_b=compute_resistance[0], plis=built_up,
                        K_D=kd, K_H=kh, K_Sb=ksb, K_T=kt, K_Zb=kzb,
                        support_lateral_aux_appuis=LATERAL, pannes_ou_tirants=TIE_ROD,
                        rive_comprimee_maintenue=COMP_EDGE, entretoises_ou_entremises=BLOCK,
                        rive_tendue_maintenue=TEN_EDGE, plis_fixes_a_au_plus_4d=PLIES_FASTENED,
                        M_f=mf, source_resistances=SOURCE, source_K_D=SOURCE_KD,
                    )
        with st.container(horizontal_alignment="center"):
            afficher_figures("Flexion (6.5.3)")

if "cisaillement" in ONGLETS:
    with ONGLETS["cisaillement"]:
        afficher_titre_de_l_onglet("Cisaillement (6.5.4)", "6.5.4.3")
        acces.avertir_si_en_test("cisaillement")
        kd, ksv, kt, kh, kzv = sawn_lumber.modification_factors(
            width=width,
            depth=depth,
            prop="cis_v",
            duration=duration[DURATION],
            loads=CHARGES,
            category=CATEGORY,
            wet_service=wet,
            treated=treated,
            incised=incised,
            _2ft_spacing=group,
            connected_subfloor=subfloor,
            built_up_beam=PLIS,
        )
        with st.container(horizontal_alignment="center"):
            col1, col2 = st.columns(2, width=550)
            with col1:
                # d_n <= 0.25 d (6.5.4.4.2, p. 66) : borne métrique exacte, arrondie vers le bas en impérial
                quart_de_d = 0.25 * depth
                notch_depth = iu.champ(
                    "Profondeur de l'entaille, $d_n$ ({unite})",
                    "dimension",
                    key="cis_d_n",
                    min_value=0.0,
                    max_value=quart_de_d,
                    placeholder="Optionnel",
                    help=f"Ne doit pas dépasser $0.25 \\cdot d$ = {iu.texte(quart_de_d, 'dimension')} (6.5.4.4.2)",
                    icon=":material/height:",
                )
                notch_length = iu.champ(
                    "Longueur de l'entaille, $e$ ({unite})",
                    "dimension",
                    key="cis_e",
                    min_value=0.0,
                    placeholder="Optionnel",
                    icon=":material/arrow_range:",
                )

            with col2:
                vf = iu.champ(
                    "$V_f: ({unite})$",
                    "force",
                    key="cis_vf",
                    min_value=0.0,
                    width=550,
                    placeholder="Cisaillement pondéré",
                    icon=":material/input:",
                )

                # Résistances calculées par le nouveau moteur seulement (issue #98) : l'onglet, le
                # Résumé et la note PDF affichent donc les mêmes valeurs.
                entaille = bool(notch_depth and notch_length)
                cisaillement = art_6_5_4.verifier_cisaillement(
                    b=width * built_up, d=depth, f_v=compute_resistance[1], plis=built_up,
                    d_n=notch_depth if entaille else 0,
                    K_D=kd, K_H=kh, K_Sv=ksv, K_T=kt, K_Zv=kzv,
                    V_f=vf, source_resistances=SOURCE, source_K_D=SOURCE_KD,
                )
                NOTE["Cisaillement (6.5.4.3)"] = cisaillement
                afficher_resistance_et_verification(cisaillement, "V_r")
                if entaille:
                    # Cisaillement par fissuration : K_H de la ligne « Autre propriété » du tableau 6.12
                    # (1.00), K_Sf du tableau 6.10 (décision de l'utilisateur, issue #98).
                    kd_f, ksf, kt_f, kh_f, _ = sawn_lumber.modification_factors(
                        width=width,
                        depth=depth,
                        prop="cis_f",
                        duration=duration[DURATION],
                        loads=CHARGES,
                        category=CATEGORY,
                        wet_service=wet,
                        treated=treated,
                        incised=incised,
                        _2ft_spacing=group,
                        connected_subfloor=subfloor,
                        built_up_beam=PLIS,
                    )
                    fissuration = art_6_5_4.verifier_cisaillement_par_fissuration(
                        b=width * built_up, d=depth, d_n=notch_depth, e=notch_length, plis=built_up,
                        K_D=kd_f, K_H=kh_f, K_Sf=ksf, K_T=kt_f, V_f=vf, source_K_D=SOURCE_KD,
                    )
                    NOTE["Cisaillement par fissuration à l'entaille (6.5.4.4)"] = fissuration
                    afficher_resistance_et_verification(fissuration, "F_r")
        with st.container(horizontal_alignment="center"):
            afficher_figures(
                "Cisaillement (6.5.4.3)", "Cisaillement par fissuration à l'entaille (6.5.4.4)"
            )

# Nom de la vérification de compression parallèle dans la note : élément simple (6.5.5) ou élément composé
# de plusieurs plis (6.5.5.4, issue #32). L'article entre parenthèses choisit la figure.
NOM_COMPRESSION_PARALLELE = (
    "Compression parallèle au fil (6.5.5)"
    if built_up == 1
    else "Compression parallèle au fil, élément composé (6.5.5.4)"
)

if "compression_parallele" in ONGLETS:
    with ONGLETS["compression_parallele"]:
        afficher_titre_de_l_onglet("Compression parallèle au fil (6.5.5)", "6.5.5")
        acces.avertir_si_en_test("compression_parallele")
        with st.container(horizontal_alignment="center"):
            kd, ksc, kt, kh, _ = sawn_lumber.modification_factors(
                width=width,
                depth=depth,
                prop="comp_para",
                duration=duration[DURATION],
                loads=CHARGES,
                category=CATEGORY,
                wet_service=wet,
                treated=treated,
                incised=incised,
                _2ft_spacing=group,
                connected_subfloor=subfloor,
                built_up_beam=PLIS,
            )
            _, kse, _, _, _ = sawn_lumber.modification_factors(
                width=width,
                depth=depth,
                prop="moe",
                duration=duration[DURATION],
                loads=CHARGES,
                category=CATEGORY,
                wet_service=wet,
                treated=treated,
                incised=incised,
                _2ft_spacing=group,
                connected_subfloor=subfloor,
                built_up_beam=PLIS,
            )
            fc_modified = sawn_lumber.compression_strength(
                fc=compute_resistance[2], kd=kd, kh=kh, ksc=ksc, kt=kt
            )
            e05 = compute_resistance[6]
            axes = None

            # Degré de retenue aux extrémités pour chaque axe (tableau A.4, annexe A informative ;
            # issue #90, retour #16) : une rangée d'icônes, avec un bouton (K_e) sous chacune, et
            # « Autre » pour entrer K_e. Par défaut : translation fixe et rotation libre aux deux
            # extrémités (K_e = 1.00). Aucun avertissement avec « Autre » : choix de l'ingénieur.
            degres = choisir_les_degres_de_retenue()

            # Élément composé de plusieurs plis (6.5.5.4, issue #32) : l'ingénieur choisit le type
            # d'assemblage (6.5.5.4.2 à 6.5.5.4.4), qui donne le coefficient de réduction (0.60, 0.75 ou
            # 0.80). Décision de l'utilisateur : Datum ne vérifie pas l'assemblage (espacements,
            # pénétration, rangées) ; les exigences de la norme sont affichées en notes sous le calcul.
            assemblage = None
            if built_up > 1:
                assemblage = st.radio(
                    "Assemblage des plis (6.5.5.4)",
                    options=list(art_6_5_5.ASSEMBLAGES),
                    format_func=lambda choix: (
                        f"{art_6_5_5.ASSEMBLAGES[choix][1]} ({art_6_5_5.ASSEMBLAGES[choix][0]})"
                    ),
                    horizontal=True,
                    key="cpa_assemblage",
                    width=550,
                    help="""Clous ou pointes : 60 % (6.5.5.4.2) ; boulons : 75 % (6.5.5.4.3) ; anneaux
                    fendus et boulons : 80 % (6.5.5.4.4) de la résistance de l'élément massif
                    équivalent, pour le flambage selon $b$ seulement (6.5.5.4.6). Les exigences
                    d'assemblage ne sont pas vérifiées par Datum.""",
                )
            compose = None  # trace de 6.5.5.4 (élément composé)

            col1, col2 = st.columns(2, width=550)
            with col1:
                length = iu.champ(
                    "Longueur de l'élément, $L$ ({unite})",
                    "longueur",
                    key="cpa_L",
                    min_value=1.0,
                    placeholder="Requis",
                    help="Longueur réelle de l'élément, utilisée pour $K_{Zc}$ (6.5.5.2.4)",
                    icon=":material/straighten:",
                )
                # Entraxe des appuis latéraux et K_e de chaque axe (6.5.5.1 : L_e = K_e L)
                entraxes = {}
                for axe, nom, icone in (
                    ("b", "largeur", ":material/fit_page_width:"),
                    ("d", "hauteur", ":material/fit_page_height:"),
                ):
                    colonne_l, colonne_k = st.columns([2, 1])
                    L_selon_axe = iu.champ(
                        f"Entraxe des appuis latéraux, flambage selon ${axe}$, "
                        f"$L_{{({axe})}}$ ({{unite}})",
                        "longueur",
                        key=f"cpa_L_selon_{axe}",
                        conteneur=colonne_l,
                        min_value=1.0,
                        placeholder="Requis",
                        help=f"""Entraxe des appuis latéraux pour le flambage selon la
                        {nom} ${axe}$ (6.5.5.1)""",
                        icon=icone,
                    )
                    if degres[axe] is None:  # « Autre » : K_e entré par l'utilisateur
                        K_e_selon_axe = colonne_k.number_input(
                            f"$K_{{e({axe})}}$",
                            min_value=0.10,
                            value=1.00,
                            step=0.05,
                            format="%.2f",
                            key=f"cpa_K_e_selon_{axe}",
                            help="Coefficient de longueur effective, $L_e = K_e L$ (6.5.5.1)",
                        )
                    else:
                        K_e_selon_axe = art_A_6_5_5_1.K_e(degres[axe])
                        colonne_k.number_input(
                            f"$K_{{e({axe})}}$",
                            value=K_e_selon_axe,
                            format="%.2f",
                            disabled=True,
                            help=f"Tableau A.4 : {degres[axe]}",
                        )
                    entraxes[axe] = (L_selon_axe, K_e_selon_axe)
                # Pas de L_b ni de L_d : L_b est la longueur d'appui dans la norme (6.5.6)
                (L_selon_b, K_e_selon_b), (L_selon_d, K_e_selon_d) = entraxes["b"], entraxes["d"]
                le_b = art_6_5_5.L_e(K_e_selon_b, L_selon_b) if L_selon_b is not None else None
                le_d = art_6_5_5.L_e(K_e_selon_d, L_selon_d) if L_selon_d is not None else None

            with col2:
                pf = iu.champ(
                    "$P_f: ({unite})$",
                    "force",
                    key="cpa_pf",
                    min_value=0.0,
                    width=550,
                    placeholder="Charge axiale pondérée",
                    icon=":material/input:",
                )
                if length is None or le_b is None or le_d is None:
                    st.info(
                        "Spécifiez $L$, $L_{(b)}$ et $L_{(d)}$ pour calculer $P_r$",
                        width=650,
                        icon=":material/info:",
                    )
                elif built_up == 1:
                    try:
                        axis_b = sawn_lumber.compression_parallel_axis(
                            dimension=width,
                            length=length,
                            effective_length=le_b,
                            fc_modified=fc_modified,
                            area=width * depth,
                            e05=e05,
                            kse=kse,
                            kt=kt,
                        )
                        axis_d = sawn_lumber.compression_parallel_axis(
                            dimension=depth,
                            length=length,
                            effective_length=le_d,
                            fc_modified=fc_modified,
                            area=width * depth,
                            e05=e05,
                            kse=kse,
                            kt=kt,
                        )
                    except ValueError as error:
                        st.error(str(error), width=650, icon=":material/error:")
                    else:
                        axes = (axis_b, axis_d)
                        pr = min(axis_b[3], axis_d[3]) / 1000
                        st.write(f"$P_r = {iu.latex_significatif(pr, 'force')}$")
                        VERIF = general_design.limit_states_design(pf, pr)
                        show_verification(VERIF)
                        NOTE["Compression parallèle au fil (6.5.5)"] = (
                            art_6_5_5.verifier_compression_parallele_au_fil(
                                b=width, d=depth, L=length,
                                L_selon_b=L_selon_b, L_selon_d=L_selon_d,
                                K_e_selon_b=K_e_selon_b, K_e_selon_d=K_e_selon_d,
                                # K_e du tableau A.4 ou entré (« Autre ») ; issue #90
                                source_K_e_selon_b=source_du_K_e(degres["b"]),
                                source_K_e_selon_d=source_du_K_e(degres["d"]),
                                f_c=compute_resistance[2], E_05=e05,
                                K_D=kd, K_H=kh, K_Sc=ksc, K_T=kt, K_SE=kse, P_f=pf,
                                source_resistances=SOURCE, source_K_D=SOURCE_KD,
                            )
                        )
                else:
                    # Élément composé de 2 plis ou plus (6.5.5.4, issue #32) : nouveau moteur seulement,
                    # comme l'onglet Compression perpendiculaire (issue #98) ; l'onglet, le Résumé et
                    # la note PDF affichent donc les mêmes valeurs. K_H vient de la colonne « Poutres
                    # composées » du tableau 6.12 (1.00 en compression, décision #7).
                    try:
                        compose = art_6_5_5.verifier_compression_parallele_element_compose(
                            largeur_d_un_pli=width, nombre_de_plis=built_up, d=depth, L=length,
                            L_selon_b=L_selon_b, L_selon_d=L_selon_d,
                            K_e_selon_b=K_e_selon_b, K_e_selon_d=K_e_selon_d,
                            source_K_e_selon_b=source_du_K_e(degres["b"]),
                            source_K_e_selon_d=source_du_K_e(degres["d"]),
                            f_c=compute_resistance[2], E_05=e05, assemblage=assemblage,
                            K_D=kd, K_H=kh, K_Sc=ksc, K_T=kt, K_SE=kse, P_f=pf,
                            source_resistances=SOURCE, source_K_D=SOURCE_KD,
                        )
                    except ValueError as error:
                        # Ex. plus de 5 plis ou plis de moins de 38 mm (6.5.5.4.1 : calcul refusé),
                        # ou C_C > 50 (6.5.5.2.2)
                        st.error(str(error), width=650, icon=":material/error:")
                    else:
                        NOTE[NOM_COMPRESSION_PARALLELE] = compose
                        afficher_resistance_et_verification(compose, "P_r")

            if compose is not None:
                # Notes de la trace : exigences d'assemblage que l'ingénieur doit faire respecter
                # (décision de l'utilisateur, issue #32). Toujours visibles, pas dans « Voir plus ».
                st.warning(
                    "**Notes (6.5.5.4)**\n\n" + "\n".join(f"- {note}" for note in compose.notes),
                    width=650,
                    icon=":material/assignment:",
                )
                with st.expander("Voir plus:", width=650):
                    # Détail tiré de la trace, étape par étape (mêmes valeurs que la note PDF)
                    for etape in compose.etapes:
                        st.markdown(
                            f"{etape.article} {etape.description} : "
                            f"${etape.formule} = {etape.substitution} = {valeur_de_l_etape(etape)}$"
                        )

            if axes:
                with st.expander("Voir plus:", width=650):
                    st.markdown(
                        f"$F_c = f_c (K_D K_H K_{{Sc}} K_T) = {compute_resistance[2]} \\cdot "
                        f"({kd} \\cdot {kh} \\cdot {ksc} \\cdot {kt}) = "
                        f"{iu.latex_significatif(fc_modified, 'contrainte')}$"
                    )
                    st.markdown(f"$E_{{05}} = {iu.latex(e05, 'contrainte')}$, $K_{{SE}} = {kse}$")
                    for label, axis in zip(
                        ("Selon $b$", "Selon $d$"), axes
                    ):
                        cc, kzc, kc, pr_axis = axis
                        st.markdown(
                            f"**{label}** : $C_c = {cc:.2f}$, $K_{{Zc}} = {kzc:.4f}$, "
                            f"$K_C = {kc:.4f}$, $P_r = {iu.latex_significatif(pr_axis / 1000, 'force')}$"
                        )
        with st.container(horizontal_alignment="center"):
            afficher_figures(NOM_COMPRESSION_PARALLELE)

if "compression_perpendiculaire" in ONGLETS:
    with ONGLETS["compression_perpendiculaire"]:
        afficher_titre_de_l_onglet("Compression perpendiculaire au fil (6.5.6)", "6.5.6.3")
        acces.avertir_si_en_test("compression_perpendiculaire")
        with st.container(horizontal_alignment="center"):
            kd, kscp, kt, _, _ = sawn_lumber.modification_factors(
                width=width,
                depth=depth,
                prop="comp_perp",
                duration=duration[DURATION],
                loads=CHARGES,
                category=CATEGORY,
                wet_service=wet,
                treated=treated,
                incised=incised,
                _2ft_spacing=group,
                connected_subfloor=subfloor,
                built_up_beam=PLIS,
            )
            member_width = built_up * width

            # --- résistance prévue fcp : tableaux 6.4 à 6.9, ou densité G en option (A.6.5.6) ---
            fcp = compute_resistance[3]
            col1, col2 = st.columns(2, width=550)
            with col1:
                use_density = st.checkbox(
                    "$f_{cp}$ à partir de la densité $G$",
                    key="cp_use_density",
                    help="""Option (annexe A.6.5.6, informative). Par défaut, $f_{cp}$ vient des
                    tableaux 6.4 à 6.9""",
                )
            if use_density:
                with col1:
                    density = st.number_input(
                        "Densité moyenne du bois anhydre, $G$",
                        min_value=0.30,
                        max_value=0.80,
                        # Valeur proposée : G du tableau A.11 (E en MPa pour le MSR et le MEL)
                        value=tableau_A_11.G(specie[SPECIE], compute_resistance[5]),
                        step=0.01,
                        key="cp_density",
                        help="Valeur proposée selon le tableau A.11",
                    )
                with col2:
                    nlga = st.checkbox(
                        "Densité marquée NLGA (sans la limite de tolérance de 0,9)",
                        key="cp_nlga",
                    )
                fcp_table = fcp
                # A.6.5.6 : f_cp (MPa) à partir de G ; la limite de tolérance de 0,9 ne s'applique
                # pas à une densité marquée NLGA
                fcp = art_A_6_5_6.f_cp(density, limite_de_tolerance=not nlga)
                if fcp > fcp_table:
                    st.warning(
                        f"""$f_{{cp}}$ calculé à partir de $G$ ({iu.texte(fcp, "contrainte")}) est plus
                        élevé que la valeur des tableaux 6.4 à 6.9 ({iu.texte(fcp_table, "contrainte")}) :
                        non conservateur.""",
                        width=550,
                        icon=":material/warning:",
                    )
            SOURCE_FCP = "A.6.5.6 (densité G)" if use_density else SOURCE

            col1, col2 = st.columns(2, width=550)
            with col1:
                # Préremplie avec la largeur de l'élément, mise à jour quand l'élément change (retour #15)
                if st.session_state.get("cp_largeur_element") != member_width:
                    st.session_state["cp_largeur_element"] = member_width
                    iu.remplir("cp_bearing_width", float(member_width))
                bearing_width_input = iu.champ(
                    "Largeur d'appui, $b$ ({unite})",
                    "dimension",
                    key="cp_bearing_width",
                    min_value=1.0,
                    placeholder=f"Largeur de l'élément = {iu.texte(member_width, 'dimension')}",
                    help="Par défaut, la largeur de l'élément. Si vide, la largeur de l'élément est utilisée.",
                    icon=":material/fit_page_width:",
                )
                bearing_width = member_width
                if bearing_width_input is not None:
                    bearing_width = min(bearing_width_input, member_width)
                    if bearing_width_input > member_width:
                        st.warning(
                            "La largeur d'appui est limitée à la largeur de l'élément "
                            f"({iu.texte(member_width, 'dimension')}).",
                            icon=":material/warning:",
                        )
                support_length = iu.champ(
                    "Longueur d'appui, $L_b$ ({unite})",
                    "dimension",
                    key="cp_support_length",
                    min_value=1.0,
                    placeholder="Requis",
                    help="Longueur d'appui parallèle au fil (6.5.6.2)",
                    icon=":material/arrow_range:",
                )
                support_far = st.checkbox(
                    f"Appui à au moins {iu.texte(75, 'dimension')} de l'extrémité",
                    key="cp_support_far",
                    help="Condition a) de 6.5.6.5 pour $K_B$",
                )
                support_low_bending = st.checkbox(
                    "Appui hors des fortes contraintes de flexion",
                    key="cp_support_low_bending",
                    help="Condition b) de 6.5.6.5 pour $K_B$",
                )
                near_load = st.checkbox(
                    "Charge à moins de $d$ du centre de l'appui",
                    key="cp_near_load",
                    help=f"""Charge appliquée à une distance du centre de l'appui inférieure ou égale
                    à la hauteur de l'élément, $d$ = {iu.texte(depth, "dimension")} (6.5.6.3)""",
                )
                if near_load:
                    load_length = iu.champ(
                        "Longueur d'appui de la charge ({unite})",
                        "dimension",
                        key="cp_load_length",
                        min_value=1.0,
                        placeholder="Requis",
                        help="Longueur d'appui de la charge, parallèle au fil (6.5.6.3.2)",
                        icon=":material/arrow_range:",
                    )
                    load_far = st.checkbox(
                        f"Charge à au moins {iu.texte(75, 'dimension')} de l'extrémité",
                        key="cp_load_far",
                        help="Condition a) de 6.5.6.5 pour $K_B$",
                    )
                    load_low_bending = st.checkbox(
                        "Charge hors des fortes contraintes de flexion",
                        key="cp_load_low_bending",
                        help="Condition b) de 6.5.6.5 pour $K_B$",
                    )

            details = []
            with col2:
                rf = iu.champ(
                    "$R_f: ({unite})$",
                    "force",
                    key="cp_rf",
                    min_value=0.0,
                    width=550,
                    placeholder="Réaction pondérée à l'appui",
                    icon=":material/input:",
                )
                if support_length is None:
                    st.info(
                        "Spécifiez la longueur d'appui pour calculer $Q_r$",
                        width=650,
                        icon=":material/info:",
                    )
                else:
                    # Résistances calculées par le nouveau moteur seulement (comme l'onglet
                    # Cisaillement, issue #98) : l'onglet, le Résumé et la note PDF affichent donc les
                    # mêmes valeurs. Le détail (« Voir plus ») est tiré de la même trace.
                    appui = (
                        art_6_5_6.verifier_compression_perpendiculaire_au_fil(
                            b=bearing_width, d=depth, L_b=support_length, f_cp=fcp,
                            K_D=kd, K_Scp=kscp, K_T=kt,
                            loin_de_l_extremite=support_far,
                            hors_fortes_contraintes_de_flexion=support_low_bending,
                            R_f=rf, largeur_element=member_width,
                            source_resistances=SOURCE_FCP, source_K_D=SOURCE_KD,
                            plis=built_up,
                        )
                    )
                    NOTE["Compression perpendiculaire au fil (6.5.6.2)"] = appui
                    afficher_resistance_et_verification(appui, "Q_r")
                    A_b = appui.etape("A_b").valeur  # mm²
                    Q_r_en_kN = appui.etape("Q_r").valeur / 1000  # N / 1000 = kN
                    details.append(
                        f"Appui : $A_b = {iu.latex(bearing_width, 'dimension')} \\cdot "
                        f"{iu.latex(support_length, 'dimension')} = {iu.latex_significatif(A_b, 'aire')}$, "
                        f"$K_B = {appui.etape('K_B').valeur:.4f}$, "
                        f"$Q_r = {iu.latex_significatif(Q_r_en_kN, 'force')}$"
                    )

                if near_load:
                    pf_near = iu.champ(
                        "$P_f: ({unite})$ près de l'appui",
                        "force",
                        key="cp_pf",
                        min_value=0.0,
                        width=550,
                        placeholder="Charge pondérée près de l'appui",
                        icon=":material/input:",
                    )
                    if support_length is None or load_length is None:
                        st.info(
                            "Spécifiez les deux longueurs d'appui pour calculer $Q'_r$",
                            width=650,
                            icon=":material/info:",
                        )
                    else:
                        # Nouveau moteur seulement, comme l'appui ci-dessus (issue #98)
                        pres_de_l_appui = (
                            art_6_5_6.verifier_compression_perpendiculaire_pres_d_un_appui(
                                b=bearing_width, d=depth, L_b_appui=support_length,
                                L_b_charge=load_length, f_cp=fcp, K_D=kd, K_Scp=kscp, K_T=kt,
                                appui_loin_de_l_extremite=support_far,
                                appui_hors_fortes_contraintes_de_flexion=support_low_bending,
                                charge_loin_de_l_extremite=load_far,
                                charge_hors_fortes_contraintes_de_flexion=load_low_bending,
                                P_f=pf_near, largeur_element=member_width,
                                source_resistances=SOURCE_FCP, source_K_D=SOURCE_KD,
                                plis=built_up,
                            )
                        )
                        NOTE["Compression perpendiculaire près d'un appui (6.5.6.3)"] = pres_de_l_appui
                        afficher_resistance_et_verification(pres_de_l_appui, "Q'_r")
                        A_b_prime = pres_de_l_appui.etape("A'_b").valeur  # mm²
                        # K_B = min(K_B à l'appui ; K_B de la charge) : la substitution de la trace
                        # montre les deux valeurs
                        K_B_pres = pres_de_l_appui.etape("K_B")
                        Q_r_prime_en_kN = pres_de_l_appui.etape("Q'_r").valeur / 1000  # N / 1000 = kN
                        details.append(
                            f"Charge près de l'appui : $A'_b = {iu.latex_significatif(A_b_prime, 'aire')}$, "
                            f"$K_B = {K_B_pres.substitution} = {K_B_pres.valeur:.4f}$, "
                            f"$Q'_r = {iu.latex_significatif(Q_r_prime_en_kN, 'force')}$"
                        )

            afficher_figures(
                "Compression perpendiculaire au fil (6.5.6.2)",
                "Compression perpendiculaire près d'un appui (6.5.6.3)",
            )

            if details:
                # details n'est rempli que si Q_r est calculé (Q'_r exige aussi L_b à l'appui) : la
                # trace « appui » existe donc ici ; F_cp et K_Zcp viennent de cette trace
                F_cp = appui.etape("F_{cp}").valeur  # MPa
                K_Zcp = appui.etape("K_{Zcp}").valeur
                with st.expander("Voir plus:", width=650):
                    st.markdown(
                        f"$F_{{cp}} = f_{{cp}} (K_D K_{{Scp}} K_T) = {fcp:.2f} \\cdot "
                        f"({kd} \\cdot {kscp} \\cdot {kt}) = {iu.latex_significatif(F_cp, 'contrainte')}$"
                    )
                    st.markdown(
                        f"$K_{{Zcp}} = {K_Zcp:.4f}$ (largeur/hauteur = "
                        f"{member_width}/{depth} = {member_width / depth:.2f})"
                    )
                    for line in details:
                        st.markdown(line)

if "compression_oblique" in ONGLETS:
    with ONGLETS["compression_oblique"]:
        afficher_titre_de_l_onglet("Compression oblique par rapport au fil (6.5.7)", "6.5.7")
        with st.container(horizontal_alignment="center"):
            st.warning("Fonctionnalité à venir.", width=200)

if "traction" in ONGLETS:
    with ONGLETS["traction"]:
        afficher_titre_de_l_onglet("Traction parallèle au fil (6.5.8)", "6.5.8")
        with st.container(horizontal_alignment="center"):
            st.warning("Fonctionnalité à venir.", width=200)

if "flexion_et_charge_axiale" in ONGLETS:
    with ONGLETS["flexion_et_charge_axiale"]:
        afficher_titre_de_l_onglet("Flexion et charge axiale combinées (6.5.9)", "6.5.9")
        with st.container(horizontal_alignment="center"):
            st.warning("Fonctionnalité à venir.", width=200)


# --- note de calcul PDF (issue #50) ---
# Vérifications de la page, dans l'ordre des onglets : (nom dans NOTE, onglet, vérification prévue).
# La vérification prévue (resume.VerificationPrevue) donne l'article et les symboles de la norme de la
# charge pondérée et de la résistance pondérée : le tableau « Résumé » et la page résumé de la note
# affichent ainsi une ligne pour chaque vérification, même si elle n'est pas encore faite
# (datum-retours #22). Les symboles sont ceux des fonctions de vérification du moteur (Verification).
# Les onglets « à venir » (compression oblique, traction, flexion et charge axiale) n'ont pas encore de
# calcul : ils ne sont pas dans le résumé.
VERIFICATIONS_DE_LA_PAGE = [
    ("Flexion (6.5.3)", "flexion",
     VerificationPrevue("Résistance au moment de flexion", "6.5.3", "M_f", "M_r", "kN·m", "moment")),
    ("Cisaillement (6.5.4.3)", "cisaillement",
     VerificationPrevue("Résistance au cisaillement", "6.5.4.3", "V_f", "V_r", "kN", "force")),
    ("Cisaillement par fissuration à l'entaille (6.5.4.4)", "cisaillement",
     VerificationPrevue(
         "Résistance au cisaillement par fissuration à l'entaille", "6.5.4.4", "V_f", "F_r", "kN", "force"
     )),
    # Compression parallèle : une seule ligne, celle de la pièce choisie (PR #114) : élément simple (6.5.5)
    # ou élément composé de plusieurs plis (6.5.5.4). Même nom que la trace (NOM_COMPRESSION_PARALLELE),
    # pour que NOTE.get(nom) la trouve ; titres et articles de la trace (verifier_compression_parallele_...).
    (NOM_COMPRESSION_PARALLELE, "compression_parallele",
     VerificationPrevue("Résistance à la compression parallèle au fil", "6.5.5", "P_f", "P_r", "kN", "force")
     if built_up == 1
     else VerificationPrevue(
         "Résistance à la compression parallèle au fil, élément composé", "6.5.5.4", "P_f", "P_r", "kN", "force"
     )),
    ("Compression perpendiculaire au fil (6.5.6.2)", "compression_perpendiculaire",
     VerificationPrevue(
         "Compression perpendiculaire au fil à l'appui", "6.5.6.2", "R_f", "Q_r", "kN", "force"
     )),
    ("Compression perpendiculaire près d'un appui (6.5.6.3)", "compression_perpendiculaire",
     VerificationPrevue(
         "Compression perpendiculaire au fil près d'un appui", "6.5.6.3", "P_f", "Q'_r", "kN", "force"
     )),
]
# Onglet de chaque vérification (accès du compte, avertissement « en test », commentaire de l'onglet)
FONCTION_DE_LA_VERIFICATION = {nom: onglet for nom, onglet, _ in VERIFICATIONS_DE_LA_PAGE}
# Vérifications offertes au compte (onglet offert, acces.py) : les autres sont absentes du résumé
# (décision de l'utilisateur, datum-retours #22)
OFFERTES = [(nom, prevue) for nom, onglet, prevue in VERIFICATIONS_DE_LA_PAGE if onglet in ONGLETS]
# Seulement les vérifications faites (charge pondérée entrée) : pas de page inutile dans la note
FAITES = {nom: r for nom, r in NOTE.items() if r.verification is not None}
# Statut affiché dans le tableau « Résumé » (couleurs de Streamlit) ; les deux derniers en gris : la
# vérification n'est pas faite
STATUT_AFFICHE = {
    CONFORME: ":green[✔ Conforme]",
    NON_CONFORME: ":red[✖ Non conforme]",
    CHARGE_MANQUANTE: ":gray[Charge manquante]",
    NON_CALCULE: ":gray[Non calculé]",
}
if acces.permis("note_pdf") and OFFERTES:
    # Résumé de toutes les vérifications offertes (issue #85, simplifié par datum-retours #22) : mêmes
    # lignes et mêmes valeurs que la page résumé de la note PDF. Colonnes : article, charge et
    # résistance pondérées en métrique seulement (même avec la bascule en impérial), ratio et statut.
    # La vérification qui gouverne (ratio le plus élevé) est en gras.
    st.divider()
    st.subheader("Résumé", anchor=False)
    # Cellulaire : le tableau a 5 colonnes de mots qui ne se coupent pas (ex. « Conforme »,
    # « Résistance ») ; avec la police et les marges par défaut, il dépasse l'écran (environ 400 px pour
    # 360 px) et la colonne Statut est coupée. Sur un petit écran seulement, texte et marges plus petits.
    st.html(
        """<style>
        @media (max-width: 640px) {
            .st-key-tableau_du_resume table { font-size: 0.8rem; }
            .st-key-tableau_du_resume :is(th, td) { padding: 0.25rem 0.3rem; }
        }
        </style>"""
    )
    with st.container(horizontal_alignment="center", key="tableau_du_resume"):
        # NOTE.get(nom) : None si la vérification n'est pas calculée (« Non calculé »)
        lignes = resume_des_verifications_offertes([("", prevue, NOTE.get(nom)) for nom, prevue in OFFERTES])
        tableau = [
            "| Article | Charge pondérée | Résistance pondérée | Ratio | Statut |",
            "|---|---|---|--:|---|",
        ]
        for ligne in lignes:
            l = formater_ligne_du_resume(ligne)  # textes en métrique, « — » si la valeur manque
            gras = "**" if l["gouverne"] else ""
            cellules = [
                l["article"],
                # « symbole = valeur », ou « — » seul si la valeur n'est pas connue
                "—" if l["charge"] == "—" else f"${l['symbole_charge']}$ = {l['charge']}",
                "—" if l["resistance"] == "—" else f"${l['symbole_resistance']}$ = {l['resistance']}",
                l["ratio"],
                STATUT_AFFICHE[l["statut"]],
            ]
            tableau.append("| " + " | ".join(f"{gras}{c}{gras}" for c in cellules) + " |")
        st.markdown("\n".join(tableau), width=900)
        st.caption("En gras : la vérification qui gouverne (ratio le plus élevé).", width=900)

# Une boîte de commentaires par onglet (datum-retours #21, décision de l'utilisateur : un par onglet,
# ex. un seul pour le cisaillement, même avec l'entaille). Elle est ajoutée à la fin de chaque onglet qui
# a au moins une vérification. Le commentaire est une donnée de la note, pas du calcul : il n'entre pas
# dans la trace (Resultat).
COMMENTAIRE_DE_L_ONGLET = {}
if acces.permis("note_pdf"):
    for onglet in dict.fromkeys(FONCTION_DE_LA_VERIFICATION.values()):  # onglets, sans doublon, en ordre
        if onglet in ONGLETS:
            with ONGLETS[onglet], st.container(horizontal_alignment="center"):
                COMMENTAIRE_DE_L_ONGLET[onglet] = st.text_area(
                    "Commentaires pour la note",
                    key=f"note_commentaire_{onglet}",
                    width=650,
                    help="Facultatif. Imprimé à la fin de la page de cette vérification dans la note "
                    "de calcul, sous le titre « Commentaires ».",
                )

if EN_TETE_DE_LA_NOTE is not None:
    # Champs de l'en-tête, affichés en haut de la page (place réservée avant « Matériaux »,
    # datum-retours #21). Toujours créés, même avant le premier calcul : ils se remplissent en premier.
    # Une rangée de 2 colonnes par paire de champs : sur un cellulaire, les colonnes s'empilent et
    # les champs restent dans l'ordre de lecture (Client, Projet, Adresse, Dossier…).
    with EN_TETE_DE_LA_NOTE:
        col1, col2 = st.columns(2)
        client = col1.text_input("Client")
        projet = col2.text_input("Projet")
        col1, col2 = st.columns(2)
        adresse = col1.text_input("Adresse du projet")
        dossier = col2.text_input("Numéro de dossier")
        # Liste des ingénieurs du compte ; un autre nom peut être tapé (datum-retours #6)
        INGENIEURS = config.ingenieurs_du_compte(st.session_state.get("compte", ""))
        OIQ_PAR_NOM = dict(INGENIEURS)
        col1, col2 = st.columns(2)
        ingenieur = col1.selectbox(
            "Ingénieur",
            options=[nom for nom, _ in INGENIEURS],
            index=None,
            accept_new_options=True,
            placeholder="Choisir ou taper un nom",
        )
        oiq = col2.text_input(
            "Numéro OIQ",
            value=OIQ_PAR_NOM.get(ingenieur, ""),
            key=f"note_oiq_{ingenieur}",  # se remplit quand l'ingénieur change
        )
        col1, col2 = st.columns(2)
        date = col1.date_input("Date", value=datetime.date.today(), format="YYYY-MM-DD")
        # Titre par défaut : la pièce calculée, ex. « 2x6 », « 3-2x6 » ou « 38x235 mm » (datum-retours #7
        # et #20), tiré de la boîte « Pièce ». Il suit la pièce choisie, sauf s'il a été modifié à la main.
        titre_par_defaut = DIMENSIONS.nom_court()
        if st.session_state.get("note_titre") in (None, st.session_state.get("note_titre_defaut")):
            st.session_state["note_titre"] = titre_par_defaut
        st.session_state["note_titre_defaut"] = titre_par_defaut
        titre = col2.text_input(
            "Titre",
            key="note_titre",
            help="Titre de chaque page ; aussi dans le nom du fichier PDF",
        )

if acces.permis("note_pdf"):
    st.divider()
    st.subheader("Note de calcul (PDF)", anchor=False)
    with st.container(horizontal_alignment="center"):
        if not FAITES:
            st.info(
                "Entrez la charge pondérée d'au moins une vérification pour produire la note de "
                "calcul.",
                width=650,
                icon=":material/info:",
            )
        else:
            with st.container(width=650):
                # Commentaires généraux : restent en bas, près du bouton (datum-retours #21)
                commentaires = st.text_area(
                    "Commentaires généraux",
                    help="En bas à gauche de la première page, à côté de la vérification et du sceau",
                )
            with st.container(width=650):
                acces.avertir_si_en_test("note_pdf")
                st.markdown("Vérifications à inclure :")
                choix = [nom for nom in FAITES if st.checkbox(nom, value=True, key=f"note_{nom}")]
                if choix:
                    # Commentaire de chaque onglet sur la page de sa première vérification incluse
                    # (datum-retours #21) : un onglet à deux vérifications (ex. cisaillement et
                    # entaille) n'imprime pas son commentaire deux fois.
                    resultats_de_la_note = []
                    onglets_deja_commentes = set()
                    for nom in choix:
                        onglet = FONCTION_DE_LA_VERIFICATION[nom]
                        commentaire = (
                            "" if onglet in onglets_deja_commentes else COMMENTAIRE_DE_L_ONGLET.get(onglet, "")
                        )
                        onglets_deja_commentes.add(onglet)
                        resultats_de_la_note.append((titre, FAITES[nom], acces.en_test(onglet), commentaire))
                    # Page résumé de la note (datum-retours #22) : mêmes lignes que le tableau « Résumé »
                    # (vérifications offertes, « Charge manquante », « Non calculé »), sauf une
                    # vérification faite mais décochée ci-dessus : elle n'est pas dans la note, donc
                    # pas dans son résumé non plus.
                    resume_de_la_note = [
                        (titre, prevue, NOTE.get(nom))
                        for nom, prevue in OFFERTES
                        if nom not in FAITES or nom in choix
                    ]
                    pdf = produire_pdf(
                        resultats_de_la_note,
                        EnTete(client, projet, adresse, dossier, str(date), ingenieur or "", oiq),
                        # Apparence du compte, sans options pour la changer (datum-retours #8)
                        config.apparence_du_compte(st.session_state.get("compte", "")),
                        commentaires,
                        verifications_offertes=resume_de_la_note,
                    )
                    st.download_button(
                        "Télécharger la note de calcul (PDF)",
                        data=pdf,
                        file_name=nom_du_pdf(titre, str(date), dossier),  # AAAAMMJJ_dossier_titre.pdf
                        mime="application/pdf",
                        icon=":material/download:",
                        type="primary",
                    )
