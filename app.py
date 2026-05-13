import streamlit as st
import pandas as pd
import requests
from PIL import Image
import io

# Inställningar för sidan
st.set_page_config(page_title="Surdegs-Analysator", page_icon="🍞", layout="wide")

# Initiera session_state för inkråmsanalysen
if 'active_image' not in st.session_state:
    st.session_state.active_image = None

API_URL = "https://surdeg-api.onrender.com"

# --- MENY I SIDOFÄLTET ---
with st.sidebar:
    st.title("👨‍🍳 Bagarens Meny")
    page = st.radio("Välj funktion:", ["🍞 Inkråms-analys", "⚖️ Receptkalkylator"])

# ==========================================
# SIDA 1: INKRÅMS-ANALYS (Din befintliga kod)
# ==========================================
if page == "🍞 Inkråms-analys":
    st.title("🍞 Surdegs-Analysator")
    st.markdown("Ladda upp en bild på ditt inkråm för AI-analys.")
    
    tab1, tab2 = st.tabs(["Ny Analys", "Historik"])
    
    with tab1:
        # HÄR LIGGER DIN BEFINTLIGA UPPLADDNINGSKOD...
        st.info("Här ligger koden för inkråmsanalys som vi byggde tidigare.")
        # Klistra in koden från 'up_file = st.file_uploader(...)' och nedåt här

    with tab2:
        # HÄR LIGGER DIN BEFINTLIGA HISTORIK-KOD...
        st.info("Här ligger koden för historik.")

# ==========================================
# SIDA 2: RECEPTKALKYLATOR (Ny funktion)
# ==========================================
elif page == "⚖️ Receptkalkylator":
    st.title("⚖️ Recept & Hydrering")
    st.markdown("Fyll i dina ingredienser för att automatiskt räkna ut Baker's Percentage och total hydrering.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Mjölsorter")
        st.write("Lägg till dina mjölsorter i tabellen nedan. Du kan redigera namnen och lägga till nya rader.")
        
        # Förinställda värden (enkel att skräddarsy)
        default_flours = pd.DataFrame(
            [
                {"Mjöltyp": "Manitoba Cream", "Vikt (g)": 400},
                {"Mjöltyp": "Durum", "Vikt (g)": 50},
                {"Mjöltyp": "Fint Rågmjöl", "Vikt (g)": 50}
            ]
        )
        
        # Interaktiv tabell där du kan lägga till/ta bort rader
        edited_flours = st.data_editor(default_flours, num_rows="dynamic", use_container_width=True)
        total_flour_added = edited_flours["Vikt (g)"].sum()

    with col2:
        st.subheader("Vätska & Övrigt")
        water = st.number_input("Vatten (g)", min_value=0, value=350, step=10)
        starter = st.number_input("Surdeg (g)", min_value=0, value=100, step=10)
        salt = st.number_input("Salt (g)", min_value=0, value=11, step=1)
        
        # Välj hydrering på din surdegsgrund (oftast 100%, dvs hälften mjöl, hälften vatten)
        starter_hydration = st.slider("Surdegens hydrering (%)", min_value=50, max_value=150, value=100, step=10)

    st.divider()

    # --- MATEMATIKEN (Baker's Math) ---
    # Beräkna hur mycket mjöl och vatten som kommer från surdegen
    starter_flour_part = starter / (1 + (starter_hydration / 100))
    starter_water_part = starter - starter_flour_part

    # Totala mängder
    total_flour = total_flour_added + starter_flour_part
    total_water = water + starter_water_part

    st.subheader("📊 Resultat & Baker's Percentage")
    
    if total_flour > 0:
        hydration = (total_water / total_flour) * 100
        salt_pct = (salt / total_flour) * 100
        
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("Total Hydrering", f"{hydration:.1f}%")
        res_col2.metric("Saltmängd", f"{salt_pct:.1f}%")
        res_col3.metric("Totalt Mjöl (inkl. surdeg)", f"{total_flour:.0f} g")
        res_col4.metric("Degens Totalvikt", f"{total_flour_added + water + starter + salt:.0f} g")

        # Visa en sammanställning av mjölfördelningen
        st.write("**Mjölfördelning (inklusive surdegen):**")
        for index, row in edited_flours.iterrows():
            if row["Vikt (g)"] > 0:
                pct = (row["Vikt (g)"] / total_flour) * 100
                st.write(f"- {row['Mjöltyp']}: {pct:.1f}%")
    else:
        st.warning("Lägg till minst en mjölsort för att se beräkningarna.")