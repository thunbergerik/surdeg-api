import streamlit as st
import requests
from PIL import Image
import io

# Inställningar för sidan
st.set_page_config(page_title="Surdegs-Analysator", page_icon="🍞", layout="wide")

# Initiera session_state för att motverka att bilden försvinner vid omladdning på Android
if 'active_image' not in st.session_state:
    st.session_state.active_image = None

st.title("🍞 Surdegs-Analysator")
st.markdown("Ladda upp en bild på ditt inkråm för AI-analys.")

API_URL = "https://surdeg-api.onrender.com"

tab1, tab2 = st.tabs(["Ny Analys", "Historik"])

with tab1:
    st.header("Ladda upp bild")
    
    # Enbart filuppladdare
    up_file = st.file_uploader("Välj en bild från galleriet...", type=["jpg", "jpeg", "png"])

    # Om en ny fil väljs, spara ner dess bytes i session_state
    if up_file is not None:
        st.session_state.active_image = up_file.getvalue()

    # Om vi har en bild i session_state, visa och processa den
    if st.session_state.active_image:
        # Öppna bilden med Pillow för förhandsvisning och skalning
        img = Image.open(io.BytesIO(st.session_state.active_image))
        
        # Säkerställ RGB-format
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Skala ner bilden direkt för att undvika timeout vid uppladdning
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size))
            
        # Spara till en buffer för att kunna skicka via API
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        final_bytes = buffer.getvalue()

        st.image(img, caption="Vald bild", width=400)
        
        if st.button("Analysera inkråm"):
            with st.spinner("AI-bagaren analyserar bilden..."):
                files = {"file": ("image.jpg", final_bytes, "image/jpeg")}
                try:
                    response = requests.post(f"{API_URL}/api/analyze", files=files, timeout=30)
                    
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
                        st.error(f"Backend svarade inte korrekt (Status: {response.status_code})")
                except requests.exceptions.Timeout:
                    st.error("Uppladdningen tog för lång tid. Kontrollera din anslutning.")

with tab2:
    # Din befintliga historik-kod här...
    st.header("Tidigare analyser")
    if st.button("Uppdatera historik"):
        # ... anrop till API_URL/api/history
        pass