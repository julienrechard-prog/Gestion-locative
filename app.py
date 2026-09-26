from datetime import datetime, timedelta
from io import BytesIO
import calendar
import urllib.parse
import json
import os
import pandas as pd
from fpdf import FPDF
import streamlit as st

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Gestion Parc Locatif",
    page_icon="☰",
    layout="wide",
)

DATA_FILE = "parc_locatif_data.json"
SIGNATURE_FILE = "signature.png"

def charger_donnees():
    """Charge les données depuis le fichier JSON local si il existe."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return None
    return None

def sauvegarder_donnees():
    """Sauvegarde l'état actuel de la session dans le fichier JSON local."""
    data = {
        "logements": st.session_state.logements,
        "parc_logements": st.session_state.parc_logements.to_dict(orient="split"),
        "loyers": st.session_state.loyers.to_dict(orient="split"),
        "travaux": st.session_state.travaux.to_dict(orient="split"),
        "contacts": st.session_state.contacts.to_dict(orient="split"),
        "agenda": st.session_state.agenda.to_dict(orient="split"),
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- INITIALISATION DES DONNÉES EN SESSION AVEC PERSISTANCE ---
saved_data = charger_donnees()

if saved_data:
    if "logements" not in st.session_state:
        st.session_state.logements = saved_data.get("logements", [f"Logement {i}" for i in range(1, 10)])
    if "parc_logements" not in st.session_state:
        st.session_state.parc_logements = pd.DataFrame(**saved_data.get("parc_logements"))
    if "loyers" not in st.session_state:
        st.session_state.loyers = pd.DataFrame(**saved_data.get("loyers"))
    if "travaux" not in st.session_state:
        st.session_state.travaux = pd.DataFrame(**saved_data.get("travaux"))
    if "contacts" not in st.session_state:
        st.session_state.contacts = pd.DataFrame(**saved_data.get("contacts"))
    if "agenda" not in st.session_state:
        st.session_state.agenda = pd.DataFrame(**saved_data.get("agenda"))
else:
    if "logements" not in st.session_state:
        st.session_state.logements = [f"Logement {i}" for i in range(1, 10)]

    if "parc_logements" not in st.session_state:
        st.session_state.parc_logements = pd.DataFrame({
            "ID": [str(i) for i in range(1, 10)],
            "Logement": st.session_state.logements,
            "Adresse": [f"Adresse par défaut {i}" for i in range(1, 10)],
            "Locataire": [f"Locataire {i}" for i in range(1, 10)],
            "Loyer HC": [600 + i * 50 for i in range(9)],
            "Charges": [50] * 9,
            "Imposition": ["Nu"] * 9,
        })

    if "loyers" not in st.session_state:
        current_month = datetime.now().strftime("%Y-%m")
        st.session_state.loyers = pd.DataFrame({
            "Logement": st.session_state.logements,
            "Locataire": st.session_state.parc_logements["Locataire"],
            "Loyer HC": st.session_state.parc_logements["Loyer HC"],
            "Charges": st.session_state.parc_logements["Charges"],
            f"Statut_{current_month}": [False] * len(st.session_state.logements),
        })

    if "travaux" not in st.session_state:
        st.session_state.travaux = pd.DataFrame(
            columns=["Logement", "Date", "Titre", "Description", "Statut"]
        )

    if "contacts" not in st.session_state:
        st.session_state.contacts = pd.DataFrame(
            columns=["Nom", "Catégorie", "Téléphone", "Email", "Notes"]
        )

    if "agenda" not in st.session_state:
        st.session_state.agenda = pd.DataFrame(
            columns=["Date", "Logement", "Événement", "Type"]
        )
    sauvegarder_donnees()

# --- BARRE LATÉRALE (NAVIGATION) ---
st.sidebar.title("☰ Gestion Locative")
menu = st.sidebar.radio(
    "Navigation",
    [
        "Tableau de bord",
        "Gestion des Logements",
        "Suivi des loyers & Quittances",
        "Travaux & Suivi",
        "Documents & États des lieux",
        "Agenda",
        "Annuaire utiles",
    ],
)


# ==========================================
# 1. TABLEAU DE BORD (AVEC GRAPHIQUE CORRIGÉ)
# ==========================================
if menu == "Tableau de bord":
    st.title("📊 Tableau de Bord & Revenus")

    total_logements = len(st.session_state.logements)
    current_month = datetime.now().strftime("%Y-%m")
    
    col_statut = f"Statut_{current_month}"
    if col_statut not in st.session_state.loyers.columns:
        st.session_state.loyers[col_statut] = False

    payés = (
        st.session_state.loyers[col_statut]
        .value_counts()
        .get(True, 0)
    )
    
    pourcentage = int(payés * 100 / total_logements) if total_logements > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Logements", total_logements)
    with col2:
        st.metric(
            f"Loyers perçus ({current_month})", f"{payés} / {total_logements}", f"{pourcentage}%"
        )
    with col3:
        en_cours = len(
            st.session_state.travaux[
                st.session_state.travaux["Statut"] == "En cours"
            ]
        )
        st.metric("Travaux en cours", en_cours)

    st.divider()
    st.subheader("📈 Graphique des revenus cumulés sur l'année")

    f_col1, f_col2, f_col3 = st.columns(3)
    
    annees_dispo = list(set([col.split("_")[1].split("-")[0] for col in st.session_state.loyers.columns if col.startswith("Statut_")]))
    if not annees_dispo:
        annees_dispo = [str(datetime.now().year)]
    annees_dispo.sort(reverse=True)

    with f_col1:
        annee_sel = st.selectbox("Année", annees_dispo)
    with f_col2:
        logements_filtre_opts = ["Tous"] + st.session_state.logements
        logement_sel = st.selectbox("Logement", logements_filtre_opts)
    with f_col3:
        imposition_opts = ["Tous", "Nu", "Meublé", "Airbnb"]
        imposition_sel = st.selectbox("Type de fiscalité (Imposition)", imposition_opts)

    mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
    revenus_mensuels = []

    for m in range(1, 13):
        mois_str = f"{annee_sel}-{m:02d}"
        col_m = f"Statut_{mois_str}"
        
        total_mois = 0.0
        for _, l_row in st.session_state.loyers.iterrows():
            log_name = l_row["Logement"]
            
            if logement_sel != "Tous" and log_name != logement_sel:
                continue
            
            parc_match = st.session_state.parc_logements[st.session_state.parc_logements["Logement"] == log_name]
            if not parc_match.empty:
                imp_val = parc_match.iloc[0]["Imposition"]
                if imposition_sel != "Tous" and imp_val != imposition_sel:
                    continue
            
            if col_m in st.session_state.loyers.columns and l_row.get(col_m, False):
                total_mois += float(l_row["Loyer HC"]) + float(l_row["Charges"])
        
        revenus_mensuels.append(total_mois)

    cumul_revenus = []
    cumul = 0.0
    for val in revenus_mensuels:
        cumul += val
        cumul_revenus.append(cumul)

    df_chart = pd.DataFrame({
        "Mois": mois_noms,
        "Revenus cumulés (€)": cumul_revenus
    })
    df_chart["Mois"] = pd.Categorical(df_chart["Mois"], categories=mois_noms, ordered=True)
    df_chart.set_index("Mois", inplace=True)

    st.line_chart(df_chart, use_container_width=True)

    st.divider()
    st.subheader("Vue rapide du parc locatif")
    st.dataframe(
        st.session_state.parc_logements, use_container_width=True, hide_index=True
    )


# ==========================================
# 2. GESTION DES LOGEMENTS
# ==========================================
elif menu == "Gestion des Logements":
    st.title("🏢 Fiches Logements & Paramétrage")

    st.subheader("Ajouter un nouveau logement")
    with st.form("form_nouveau_logement"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nouveau_id = st.text_input("ID du logement (ex: L01)")
            nouveau_nom = st.text_input("Nom personnalisé (ex: T2 1er étage)")
        with col2:
            nouvelle_adresse = st.text_input("Adresse du logement (ex: 5 Avenue du Maréchal Joffre, 31800 Saint-Gaudens)")
            nouveau_locataire = st.text_input("Nom du locataire (ex: Mlle Andrea Ballester)")
        with col3:
            nouveau_loyer = st.number_input("Montant Loyer HC (€)", min_value=0.0, value=440.0, step=10.0)
            nouvelles_charges = st.number_input("Montant Charges (€)", min_value=0.0, value=10.0, step=5.0)

        nouvelle_imposition = st.selectbox("Imposition", ["Nu", "Meublé", "Airbnb"])

        submit_logement = st.form_submit_button("Créer et ajouter au parc")

        if submit_logement:
            if not nouveau_id.strip() or not nouveau_nom.strip():
                st.error("L'ID et le Nom du logement ne peuvent pas être vides.")
            elif nouveau_nom in st.session_state.logements:
                st.error("Ce nom de logement existe déjà.")
            else:
                st.session_state.logements.append(nouveau_nom)

                new_parc_row = pd.DataFrame([{
                    "ID": nouveau_id,
                    "Logement": nouveau_nom,
                    "Adresse": nouvelle_adresse,
                    "Locataire": nouveau_locataire,
                    "Loyer HC": nouveau_loyer,
                    "Charges": nouvelles_charges,
                    "Imposition": nouvelle_imposition,
                }])
                st.session_state.parc_logements = pd.concat([st.session_state.parc_logements, new_parc_row], ignore_index=True)
                
                sauvegarder_donnees()
                st.success(f"Le logement '{nouveau_nom}' a été créé avec succès !")
                st.rerun()

    st.divider()
    st.subheader("Liste et modification des logements existants")
    st.info("Vous pouvez modifier directement les informations dans le tableau ci-dessous.")

    edited_parc = st.data_editor(
        st.session_state.parc_logements,
        use_container_width=True,
        hide_index=True,
        key="editor_parc_complet"
    )

    if not edited_parc.equals(st.session_state.parc_logements):
        st.session_state.parc_logements = edited_parc
        st.session_state.logements = edited_parc["Logement"].tolist()
        sauvegarder_donnees()


# ==========================================
# 3. SUIVI DES LOYERS & QUITTANCES
# ==========================================
elif menu == "Suivi des loyers & Quittances":
    st.title("💶 Suivi des Loyers & Génération de Quittances")

    current_month = st.selectbox(
        "Sélectionner le mois",
        [
            "2026-09",
            "2026-08",
            "2026-07",
            "2026-06",
            "2026-05",
            "2026-04",
            "2026-03",
            "2026-02",
            "2026-01",
        ],
    )

    col_statut = f"Statut_{current_month}"
    if col_statut not in st.session_state.loyers.columns:
        st.session_state.loyers[col_statut] = False

    data_changed = False
    for _, row in st.session_state.parc_logements.iterrows():
        log_name = row["Logement"]
        locataire = row["Locataire"]
        loyer_hc = row["Loyer HC"]
        charges = row["Charges"]
        
        mask = st.session_state.loyers["Logement"] == log_name
        if mask.any():
            if (st.session_state.loyers.loc[mask, "Locataire"].values[0] != locataire or
                st.session_state.loyers.loc[mask, "Loyer HC"].values[0] != loyer_hc or
                st.session_state.loyers.loc[mask, "Charges"].values[0] != charges):
                st.session_state.loyers.loc[mask, "Locataire"] = locataire
                st.session_state.loyers.loc[mask, "Loyer HC"] = loyer_hc
                st.session_state.loyers.loc[mask, "Charges"] = charges
                data_changed = True
        else:
            new_row = {
                "Logement": log_name,
                "Locataire": locataire,
                "Loyer HC": loyer_hc,
                "Charges": charges,
            }
            for col in st.session_state.loyers.columns:
                if col.startswith("Statut_"):
                    new_row[col] = False
            if col_statut not in new_row:
                new_row[col_statut] = False
            st.session_state.loyers = pd.concat([st.session_state.loyers, pd.DataFrame([new_row])], ignore_index=True)
            data_changed = True

    st.session_state.loyers = st.session_state.loyers[
        st.session_state.loyers["Logement"].isin(st.session_state.parc_logements["Logement"])
    ].reset_index(drop=True)

    if data_changed:
        sauvegarder_donnees()

    st.subheader("État des encaissements")
    edited_loyers = st.data_editor(
        st.session_state.loyers[["Logement", "Locataire", "Loyer HC", "Charges", col_statut]],
        use_container_width=True,
        hide_index=True,
    )
    
    if not st.session_state.loyers[col_statut].equals(edited_loyers[col_statut]):
        st.session_state.loyers[col_statut] = edited_loyers[col_statut]
        sauvegarder_donnees()

    st.divider()
    st.subheader("📄 Génération de Quittance de Loyer (Modèle F fidèle)")

    if len(st.session_state.logements) == 0:
        st.warning("Aucun logement disponible. Veuillez en créer un dans l'onglet 'Gestion des Logements'.")
    else:
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            selected_logement = st.selectbox(
                "Choisir le logement", st.session_state.logements
            )
            
            parc_info = st.session_state.parc_logements.loc[
                st.session_state.parc_logements["Logement"] == selected_logement
            ].iloc[0]
            
            nom_locataire = st.text_input(
                "Nom du locataire", value=parc_info["Locataire"]
            )
            adresse_logement_str = st.text_input(
                "Adresse du bien", value=parc_info["Adresse"]
            )
        with col_q2:
            loyer_hc = st.number_input(
                "Montant Hors Charges (€)", value=float(parc_info["Loyer HC"])
            )
            charges = st.number_input(
                "Charges (€)", value=float(parc_info["Charges"])
            )
            date_paiement = st.date_input("Date effective du paiement", value=datetime.now())

        st.markdown("### Informations du Bailleur & Signature")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            bailleur_nom = st.text_input("Nom du bailleur", value="M. JULIEN RECHARD")
            bailleur_adresse = st.text_input("Adresse du bailleur", value="22 RUE MARCEL PAGNOL, 31700 BLAGNAC")
        with b_col2:
            bailleur_tel = st.text_input("Téléphone du bailleur", value="TEL +33664288912")
            
            # Gestion du fichier de signature image avec bouton de validation explicite
            uploaded_sig = st.file_uploader("Télécharger votre image de signature (PNG/JPG)", type=["png", "jpg", "jpeg"])
            if uploaded_sig is not None:
                if st.button("Enregistrer la signature"):
                    with open(SIGNATURE_FILE, "wb") as f:
                        f.write(uploaded_sig.getbuffer())
                    st.success("Signature enregistrée avec succès !")

        if os.path.exists(SIGNATURE_FILE):
            st.info("✓ Image de signature active détectée pour les quittances.")

        if st.button("Générer la quittance PDF conforme"):
            annee, mois = map(int, current_month.split("-"))
            dernier_jour = calendar.monthrange(annee, mois)[1]
            date_debut = f"01/{mois:02d}/{annee}"
            date_fin = f"{dernier_jour:02d}/{mois:02d}/{annee}"
            
            noms_mois = {
                1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
                7: "JUILLET", 8: "AOUT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"
            }
            titre_mois_str = f"QUITTANCE {noms_mois[mois]} {annee}"
            total_paye = loyer_hc + charges
            date_paiement_str = date_paiement.strftime("%d/%m/%Y")

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)

            pdf.cell(0, 5, txt="DE", ln=True)
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 5, txt=bailleur_nom, ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 5, txt=bailleur_adresse, ln=True)
            pdf.cell(0, 5, txt="FRANCE", ln=True)
            pdf.cell(0, 5, txt=bailleur_tel, ln=True)
            pdf.ln(5)

            pdf.cell(0, 5, txt="A", ln=True)
            pdf.set_font("Arial", style="B", size=10)
            pdf.cell(0, 5, txt=nom_locataire, ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 5, txt=adresse_logement_str, ln=True)
            pdf.cell(0, 5, txt="FRANCE", ln=True)
            pdf.cell(0, 5, txt="Locataire", ln=True)
            pdf.ln(5)

            pdf.cell(0, 5, txt=f"Date {date_paiement_str}", ln=True)
            pdf.cell(0, 5, txt=f"Période {date_debut}-{date_fin}", ln=True)
            pdf.ln(4)

            pdf.set_font("Arial", style="B", size=11)
            pdf.cell(0, 8, txt=titre_mois_str, ln=True, align="C")
            pdf.ln(2)

            pdf.set_font("Arial", size=6)
            pdf.multi_cell(0, 3.5, txt="EN CAS DE CONGE OU SI L'INTERESSE N'A PAS LA QUALITE DE LOCATAIRE LE PRESENT REÇU NE CONSTITUE PAS UNE QUITTANCE DE LOYER MAIS UN SIMPLE REÇU D'INDEMNITE D'OCCUPATION", align="C")
            pdf.ln(6)

            pdf.set_font("Arial", style="B", size=9)
            pdf.cell(0, 5, txt="DÉTAILS DU TERME", ln=True)
            pdf.set_font("Arial", size=9)
            
            pdf.cell(130, 5, txt="Loyer", border=0)
            pdf.cell(60, 5, txt=f"{loyer_hc:.2f} EUR", border=0, align="R", ln=True)
            
            pdf.cell(130, 5, txt="Charges", border=0)
            pdf.cell(60, 5, txt=f"{charges:.2f} EUR", border=0, align="R", ln=True)

            pdf.set_font("Arial", style="B", size=9)
            pdf.cell(130, 5, txt="Loyer charges comprises", border=0)
            pdf.cell(60, 5, txt=f"{total_paye:.2f} EUR", border=0, align="R", ln=True)
            pdf.ln(6)

            pdf.set_font("Arial", style="B", size=9)
            pdf.cell(0, 5, txt="LOCATAIRE", ln=True)
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 4, txt=nom_locataire, ln=True)
            pdf.cell(0, 4, txt=f"Locataire a payé {total_paye:.2f} EUR le {date_paiement_str}", ln=True)
            pdf.cell(0, 4, txt=f"Correspondant à la location du bien situé au {adresse_logement_str},", ln=True)
            pdf.cell(0, 4, txt=f"Pour la période du {date_debut} au {date_fin}", ln=True)
            pdf.ln(6)

            pdf.set_font("Arial", style="B", size=9)
            pdf.cell(130, 6, txt="TOTAL PAYÉ", border=1)
            pdf.cell(60, 6, txt=f"{total_paye:.2f} EUR", border=1, align="R", ln=True)
            pdf.ln(8)

            # Insertion de l'image de signature si elle existe
            if os.path.exists(SIGNATURE_FILE):
                try:
                    pdf.image(SIGNATURE_FILE, x=135, y=pdf.get_y(), w=45)
                    pdf.ln(25)
                except Exception:
                    pdf.set_font("Arial", style="B", size=10)
                    pdf.cell(0, 4, txt="Julien RECHARD", ln=True, align="R")
            else:
                pdf.set_font("Arial", style="B", size=10)
                pdf.cell(0, 4, txt="Julien RECHARD", ln=True, align="R")

            pdf_output = BytesIO(pdf.output(dest="S").encode("latin1", errors="ignore"))
            st.download_button(
                label="📥 Télécharger la quittance PDF",
                data=pdf_output,
                file_name=f"quittance_{selected_logement}_{current_month}.pdf",
                mime="application/pdf",
            )


# ==========================================
# 4. TRAVAUX & SUIVI
# ==========================================
elif menu == "Travaux & Suivi":
    st.title("🛠️ Suivi des Travaux et Interventions")
    if len(st.session_state.logements) == 0:
        st.warning("Veuillez d'abord créer un logement.")
    else:
        with st.form("form_travaux"):
            col1, col2 = st.columns(2)
            with col1:
                logement = st.selectbox("Logement concerné", st.session_state.logements)
                titre = st.text_input("Titre de l'intervention (ex: Fuite chauffe-eau)")
            with col2:
                statut = st.selectbox("Statut", ["À planifier", "En cours", "Terminé"])
                date_travaux = st.date_input("Date")

            description = st.text_area("Notes textuelles / Détails")
            photo = st.file_uploader(
                "Ajouter une photo justificative", type=["jpg", "png", "jpeg"]
            )

            submitted = st.form_submit_button("Ajouter l'intervention")
            if submitted:
                new_row = pd.DataFrame({
                    "Logement": [logement],
                    "Date": [str(date_travaux)],
                    "Titre": [titre],
                    "Description": [description],
                    "Statut": [statut],
                })
                st.session_state.travaux = pd.concat(
                    [st.session_state.travaux, new_row], ignore_index=True
                )
                sauvegarder_donnees()
                st.success("Intervention enregistrée avec succès !")

    st.subheader("Historique des travaux")
    if not st.session_state.travaux.empty:
        st.dataframe(
            st.session_state.travaux, use_container_width=True, hide_index=True
        )
    else:
        st.info("Aucun travail enregistré pour le moment.")


# ==========================================
# 5. DOCUMENTS & ÉTATS DES LIEUX
# ==========================================
elif menu == "Documents & États des lieux":
    st.title("📂 Gestion des Documents & États des Lieux")
    if len(st.session_state.logements) == 0:
        st.warning("Veuillez d'abord créer un logement.")
    else:
        selected_logement = st.selectbox(
            "Sélectionner le logement pour voir/ajouter des pièces",
            st.session_state.logements,
        )

        doc_type = st.selectbox(
            "Type de document",
            [
                "État des lieux d'entrée",
                "État des lieux de sortie",
                "Bail de location",
                "Pièce d'identité / Autre",
            ],
        )
        uploaded_file = st.file_uploader(
            "Télécharger le document (PDF, Image)", type=["pdf", "png", "jpg"]
        )

        if uploaded_file is not None:
            if st.button("Enregistrer le document"):
                st.success(
                    f"Document '{uploaded_file.name}' enregistré pour {selected_logement}"
                    " (Stockage local simulé)."
                )

        st.divider()
        st.subheader("Documents archivés (Exemple)")
        st.write(f"Aucun document répertorié pour l'instant pour {selected_logement}.")


# ==========================================
# 6. AGENDA
# ==========================================
elif menu == "Agenda":
    st.title("📅 Agenda des Événements & Google Agenda")
    if len(st.session_state.logements) == 0:
        st.warning("Veuillez d'abord créer un logement.")
    else:
        with st.form("form_agenda"):
            col1, col2 = st.columns(2)
            with col1:
                date_ev = st.date_input("Date de l'événement")
                logement = st.selectbox("Logement", st.session_state.logements)
            with col2:
                type_ev = st.selectbox(
                    "Type",
                    [
                        "Visite / État des lieux",
                        "Fin de bail",
                        "Intervention artisan",
                        "Autre",
                    ],
                )
                titre_ev = st.text_input("Intitulé")

            submitted_ag = st.form_submit_button("Ajouter à l'agenda")
            if submitted_ag:
                new_ag = pd.DataFrame({
                    "Date": [str(date_ev)],
                    "Logement": [logement],
                    "Événement": [titre_ev],
                    "Type": [type_ev],
                })
                st.session_state.agenda = pd.concat(
                    [st.session_state.agenda, new_ag], ignore_index=True
                )
                sauvegarder_donnees()
                st.success("Événement ajouté avec succès !")

    if not st.session_state.agenda.empty:
        st.subheader("Liste de vos événements")
        
        agenda_df = st.session_state.agenda.sort_values(by="Date")
        
        for idx, row in agenda_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 4, 2])
                with c1:
                    st.markdown(f"**Date :** {row['Date']}")
                    st.markdown(f"**Logement :** {row['Logement']}")
                with c2:
                    st.markdown(f"**Type :** {row['Type']}")
                    st.markdown(f"**Intitulé :** {row['Événement']}")
                with c3:
                    d = datetime.strptime(row['Date'], "%Y-%m-%d")
                    d_end = d + timedelta(days=1)
                    dates_fmt = f"{d.strftime('%Y%m%d')}/{d_end.strftime('%Y%m%d')}"
                    
                    title_enc = urllib.parse.quote(f"[{row['Type']}] {row['Événement']}")
                    details_enc = urllib.parse.quote(f"Logement concerné : {row['Logement']}")
                    loc_enc = urllib.parse.quote(str(row['Logement']))
                    
                    gcal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title_enc}&dates={dates_fmt}&details={details_enc}&location={loc_enc}"
                    
                    st.markdown(f"[📅 Ajouter à Google Agenda]({gcal_url})", unsafe_allow_html=True)
                st.divider()
    else:
        st.info("Aucun événement à venir.")


# ==========================================
# 7. ANNUAIRE UTILES
# ==========================================
elif menu == "Annuaire utiles":
    st.title("📇 Annuaire des Contacts Utiles")
    with st.form("form_contact"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nom / Entreprise (ex: Plombier Dupont)")
            categorie = st.selectbox(
                "Catégorie",
                ["Artisan / Dépanneur", "Syndic", "Assurance", "Fournisseur", "Autre"],
            )
        with c2:
            tel = st.text_input("Téléphone")
            email = st.text_input("Email")
        notes = st.text_area("Notes / Spécificités")

        if st.form_submit_button("Ajouter le contact"):
            new_c = pd.DataFrame({
                "Nom": [nom],
                "Catégorie": [categorie],
                "Téléphone": [tel],
                "Email": [email],
                "Notes": [notes],
            })
            st.session_state.contacts = pd.concat(
                [st.session_state.contacts, new_c], ignore_index=True
            )
            sauvegarder_donnees()
            st.success("Contact enregistré.")

    if not st.session_state.contacts.empty:
        st.dataframe(
            st.session_state.contacts, use_container_width=True, hide_index=True
        )
    else:
        st.info("Votre annuaire est vide.")
