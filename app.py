import streamlit as st
import requests
import pandas as pd
from PIL import Image
import io

# Inställningar för sidan
st.set_page_config(page_title="Surdegs-Analysator", page_icon="🍞", layout="wide")

st.title("🍞 Surdegs-Analysator")
st.markdown("Analysera ditt inkråm och följ din utveckling över tid.")

API_URL = "https://surdeg-api.onrender.com"

tab1, tab2 = st.tabs(["Ny Analys", "Historik"])

with tab1:
    st.header("Ladda upp bild")
    
    # Använd två flikar för att Android-användare ska kunna välja den stabilare kameran
    upload_mode = st.radio("Välj metod:", ["Kamera (Stabilast för Android)", "Välj fil från galleri"], horizontal=True)
    
    if upload_mode == "Kamera (Stabilast för Android)":
        source_file = st.camera_input("Ta en bild på ditt bröd")
    else:
        source_file = st.file_uploader("Välj en bild...", type=["jpg", "jpeg", "png"])

    if source_file is not None:
        # --- PILLOW-LOGIK START ---
        # Öppna bilden med Pillow
        img = Image.open(source_file)
        
        # Omvandla till RGB (vissa mobiler sparar i format som inte gillas av alla API:er)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Skala ner bilden om den är för stor (sparar massor av tid vid uppladdning)
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size))
        
        # Spara ner den komprimerade bilden i en byte-buffer
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85) # 85 är perfekt balans mellan kvalité och storlek
        processed_bytes = buffer.getvalue()
        # --- PILLOW-LOGIK SLUT ---

        st.image(img, caption="Redo för analys", width=400)
        
        if st.button("Analysera inkråm"):
            with st.spinner("AI-bagaren tänker..."):
                # Vi skickar processed_bytes istället för originalfilen
                files = {"file": ("image.jpg", processed_bytes, "image/jpeg")}
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
                    st.error(f"Kunde inte nå backend-servern (Status: {response.status_code})")

with tab2:
    # ... din befintliga historik-kod ...
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