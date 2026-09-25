from datetime import datetime
from io import BytesIO
import os
import pandas as pd
from fpdf import FPDF
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Gestion Parc Locatif (9 Logements)",
    page_icon="🏠",
    layout="wide",
)

# --- INITIALISATION DES DONNÉES EN SESSION ---
if "logements" not in st.session_state:
  st.session_state.logements = [
      f"Logement {i}" for i in range(1, 10)
  ] # Vos 9 logements

if "loyers" not in st.session_state:
  # État des loyers par défaut (Mois en cours)
  current_month = datetime.now().strftime("%Y-%m")
  st.session_state.loyers = pd.DataFrame({
      "Logement": st.session_state.logements,
      "Locataire": [f"Locataire {i}" for i in range(1, 10)],
      "Loyer HC": [600 + i * 50 for i in range(9)],
      "Charges": [50] * 9,
      f"Statut_{current_month}": [False] * 9,
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

# --- BARRE LATÉRALE (NAVIGATION) ---
st.sidebar.title("🏠 Gestion Locative")
menu = st.sidebar.radio(
    "Navigation",
    [
        "Tableau de bord",
        "Suivi des loyers & Quittances",
        "Travaux & Suivi",
        "Documents & États des lieux",
        "Agenda",
        "Annuaire utiles",
    ],
)

# ==========================================
# 1. TABLEAU DE BORD
# ==========================================
if menu == "Tableau de bord":
  st.title("📊 Tableau de Bord")

  col1, col2, col3 = st.columns(3)
  with col1:
    st.metric("Total Logements", len(st.session_state.logements))
  with col2:
    current_month = datetime.now().strftime("%Y-%m")
    payés = (
        st.session_state.loyers[f"Statut_{current_month}"]
        .value_counts()
        .get(True, 0)
    )
    st.metric(
        f"Loyers perçus ({current_month})", f"{payés} / 9", f"{payés*100//9}%"
    )
  with col3:
    en_cours = len(
        st.session_state.travaux[
            st.session_state.travaux["Statut"] == "En cours"
        ]
    )
    st.metric("Travaux en cours", en_cours)

  st.divider()
  st.subheader("Vue rapide des 9 logements")
  st.dataframe(
      st.session_state.loyers, use_container_width=True, hide_index=True
  )

# ==========================================
# 2. SUIVI DES LOYERS & QUITTANCES
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

  # S'assurer que la colonne du mois existe
  col_statut = f"Statut_{current_month}"
  if col_statut not in st.session_state.loyers.columns:
    st.session_state.loyers[col_statut] = False

  st.subheader("État des encaissements")
  edited_loyers = st.data_editor(
      st.session_state.loyers[["Logement", "Locataire", "Loyer HC", "Charges", col_statut]],
      use_container_width=True,
      hide_index=True,
  )
  st.session_state.loyers[col_statut] = edited_loyers[col_statut]

  st.divider()
  st.subheader("📄 Génération de Quittance de Loyer (PDF)")

  col_q1, col_q2 = st.columns(2)
  with col_q1:
    selected_logement = st.selectbox(
        "Choisir le logement", st.session_state.logements
    )
    locataire_info = st.session_state.loyers.loc[
        st.session_state.loyers["Logement"] == selected_logement
    ].iloc[0]
    nom_locataire = st.text_input(
        "Nom du locataire", value=locataire_info["Locataire"]
    )
  with col_q2:
    loyer_hc = st.number_input(
        "Montant Hors Charges (€)", value=float(locataire_info["Loyer HC"])
    )
    charges = st.number_input(
        "Charges (€)", value=float(locataire_info["Charges"])
    )

  if st.button("Générer la quittance PDF"):
    # Création du PDF basique
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(
        200, 10, txt="QUITTANCE DE LOYER", ln=True, align="C"
    )
    pdf.ln(10)
    pdf.cell(
        200,
        10,
        txt=f"Mois : {current_month}",
        ln=True,
    )
    pdf.cell(
        200,
        10,
        txt=f"Logement : {selected_logement}",
        ln=True,
    )
    pdf.cell(
        200,
        10,
        txt=f"Locataire : {nom_locataire}",
        ln=True,
    )
    pdf.ln(10)
    pdf.cell(
        200,
        10,
        txt=f"Loyer Hors Charges : {loyer_hc:.2f} EUR",
        ln=True,
    )
    pdf.cell(
        200,
        10,
        txt=f"Provisions pour charges : {charges:.2f} EUR",
        ln=True,
    )
    pdf.cell(
        200,
        10,
        txt=f"Total payé : {loyer_hc + charges:.2f} EUR",
        ln=True,
    )
    pdf.ln(20)
    pdf.cell(
        200,
        10,
        txt="Quittance générée automatiquement par votre application web.",
        ln=True,
    )

    pdf_output = BytesIO(pdf.output(dest="S").encode("latin1"))
    st.download_button(
        label="📥 Télécharger la quittance (PDF)",
        data=pdf_output,
        file_name=f"quittance_{selected_logement}_{current_month}.pdf",
        mime="application/pdf",
    )

# ==========================================
# 3. TRAVAUX & SUIVI
# ==========================================
elif menu == "Travaux & Suivi":
  st.title("🛠️ Suivi des Travaux et Interventions")

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
      st.success("Intervention enregistrée avec succès !")

  st.subheader("Historique des travaux")
  if not st.session_state.travaux.empty:
    st.dataframe(
        st.session_state.travaux, use_container_width=True, hide_index=True
    )
  else:
    st.info("Aucun travail enregistré pour le moment.")

# ==========================================
# 4. DOCUMENTS & ÉTATS DES LIEUX
# ==========================================
elif menu == "Documents & États des lieux":
  st.title("📂 Gestion des Documents & États des Lieux")

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
# 5. AGENDA
# ==========================================
elif menu == "Agenda":
  st.title("📅 Agenda des Événements")

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
      st.success("Événement ajouté.")

  if not st.session_state.agenda.empty:
    st.dataframe(
        st.session_state.agenda.sort_values(by="Date"),
        use_container_width=True,
        hide_index=True,
    )
  else:
    st.info("Aucun événement à venir.")

# ==========================================
# 6. ANNUAIRE UTILES
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
      st.success("Contact enregistré.")

  if not st.session_state.contacts.empty:
    st.dataframe(
        st.session_state.contacts, use_container_width=True, hide_index=True
    )
  else:
    st.info("Votre annuaire est vide.")
