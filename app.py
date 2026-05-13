import streamlit as st
import requests
import pandas as pd

# Inställningar för sidan
st.set_page_config(page_title="Surdegs-Analysator", page_icon="🍞", layout="wide")

st.title("🍞 Surdegs-Analysator")
st.markdown("Analysera ditt inkråm och följ din utveckling över tid.")

# URL till din FastAPI-backend
API_URL = "https://surdeg-api.onrender.com/"

# Skapa flikar för att dela upp verktyget
tab1, tab2 = st.tabs(["Ny Analys", "Historik"])

with tab1:
    st.header("Ladda upp bild")
    uploaded_file = st.file_uploader("Välj en bild på ditt bröd...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Ditt mästerverk", width=400)
        
        if st.button("Analysera inkråm"):
            with st.spinner("AI-bagaren tänker..."):
                # Skicka bilden till FastAPI
                files = {"file": uploaded_file.getvalue()}
                response = requests.post(f"{API_URL}/api/analyze", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Diagnos: {data['2_diagnos']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Observation")
                        st.write(data['1_visuell_observation'])
                        st.metric("Konfidens", f"{data['5_konfidens_score']}%")
                    
                    with col2:
                        st.subheader("Råd för nästa bak")
                        for rad in data['4_rad_for_nasta_bak']:
                            st.write(f"• {rad}")
                else:
                    st.error("Kunde inte nå backend-servern.")

with tab2:
    st.header("Tidigare analyser")
    if st.button("Uppdatera historik"):
        response = requests.get(f"{API_URL}/api/history")
        if response.status_code == 200:
            history = response.json()
            
            for entry in history:
                analysis = entry['ai_analysis']
                with st.expander(f"{entry['created_at'][:10]} - {analysis['2_diagnos']}"):
                    st.write(f"**Observation:** {analysis['1_visuell_observation']}")
                    st.write(f"**Teknisk förklaring:** {analysis['3_teknisk_forklaring']}")
                    st.write("**Råd:**")
                    for r in analysis['4_rad_for_nasta_bak']:
                        st.write(f"- {r}")
        else:
            st.warning("Hittade ingen historik.")