import streamlit as st
import requests
import pandas as pd
from PIL import Image
import io
import json

# ==========================================
# 1. GRUNDINSTÄLLNINGAR & HJÄLPFUNKTIONER
# ==========================================
st.set_page_config(page_title="Surdegs-Analysator", page_icon="🍞", layout="wide")

API_URL = "https://surdeg-backend.onrender.com"

# Håller koll på uppladdade bilder för att undvika Androids minnes-refresh
if 'quick_crumb' not in st.session_state:
    st.session_state.quick_crumb = None
if 'log_crumb' not in st.session_state:
    st.session_state.log_crumb = None
if 'log_crust' not in st.session_state:
    st.session_state.log_crust = None

# Funktion för att komprimera bilder snabbt och säkert
def compress_image(image_bytes, max_size=1024, quality=80):
    if not image_bytes:
        return None
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()

# ==========================================
# 2. SIDOMENY FÖR NAVIGERING
# ==========================================
with st.sidebar:
    st.title("👨‍🍳 Bagarens Meny")
    page = st.radio("Välj funktion:", ["🍞 Snabb Inkråms-analys", "⚖️ Logga komplett bak"])
    st.divider()
    st.caption("Backend ansluten: ✅")

# ==========================================
# 3. SIDA 1: SNABB INKRÅMS-ANALYS
# ==========================================
if page == "🍞 Snabb Inkråms-analys":
    st.title("🍞 Snabb Inkråms-analys")
    st.markdown("Få omedelbar feedback på ditt inkråm utan att logga ett helt recept.")
    
    tab1, tab2 = st.tabs(["Ny Analys", "Historik"])
    
    with tab1:
        st.header("Ladda upp inkråm")
        up_file = st.file_uploader("Välj en bild från galleriet...", type=["jpg", "jpeg", "png"], key="quick_upload")

        if up_file is not None:
            st.session_state.quick_crumb = up_file.getvalue()

        if st.session_state.quick_crumb:
            final_bytes = compress_image(st.session_state.quick_crumb)
            st.image(final_bytes, caption="Redo för analys", width=400)
            
            if st.button("Analysera inkråm", type="primary"):
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
                            st.error(f"Ett fel uppstod: Status {response.status_code}")
                    except requests.exceptions.Timeout:
                        st.error("Anropet tog för lång tid. Kontrollera din anslutning.")

    with tab2:
        st.header("Tidigare analyser")
        if st.button("Uppdatera historik"):
            response = requests.get(f"{API_URL}/api/history")
            if response.status_code == 200:
                history = response.json()
                for entry in history:
                    analysis = entry.get('ai_analysis', {})
                    if analysis:
                        with st.expander(f"{entry['created_at'][:10]} - {analysis.get('2_diagnos', 'Okänd')}"):
                            st.write(f"**Observation:** {analysis.get('1_visuell_observation', '')}")
                            st.write(f"**Förklaring:** {analysis.get('3_teknisk_forklaring', '')}")
                            st.write("**Råd:**")
                            for r in analysis.get('4_rad_for_nasta_bak', []):
                                st.write(f"- {r}")
            else:
                st.warning("Kunde inte hämta historiken.")

# ==========================================
# 4. SIDA 2: RECEPTKALKYLATOR & LOGG
# ==========================================
elif page == "⚖️ Logga komplett bak":
    st.title("📖 Receptkalkylator & Bak-logg")
    st.markdown("Räkna ut hydrering och spara receptet tillsammans med bilder och betyg.")
    
    st.divider()
    
    # --- DEL A: RECEPT OCH HYDRERING ---
    st.subheader("1. Receptet")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("**Mjölsorter**")
        default_flours = pd.DataFrame([
            {"Mjöltyp": "Manitoba Cream", "Vikt (g)": 400},
            {"Mjöltyp": "Durum", "Vikt (g)": 50},
            {"Mjöltyp": "Fint Rågmjöl", "Vikt (g)": 50}
        ])
        edited_flours = st.data_editor(default_flours, num_rows="dynamic", use_container_width=True)
        total_flour_added = edited_flours["Vikt (g)"].sum()

    with col2:
        st.write("**Vätska & Övrigt**")
        water = st.number_input("Vatten (g)", min_value=0, value=350, step=10)
        starter = st.number_input("Surdeg (g)", min_value=0, value=100, step=10)
        salt = st.number_input("Salt (g)", min_value=0, value=11, step=1)
        starter_hydration = st.slider("Surdegens hydrering (%)", min_value=50, max_value=150, value=100, step=10)

    # Matematiken (Baker's Math)
    starter_flour_part = starter / (1 + (starter_hydration / 100))
    starter_water_part = starter - starter_flour_part
    total_flour = total_flour_added + starter_flour_part
    total_water = water + starter_water_part

    st.info("📊 **Faktisk Degkalkyl:**")
    if total_flour > 0:
        hydration = (total_water / total_flour) * 100
        salt_pct = (salt / total_flour) * 100
        
        res_col1, res_col2, res_col3, res_col4 = st.columns(4)
        res_col1.metric("Hydrering", f"{hydration:.1f}%")
        res_col2.metric("Saltmängd", f"{salt_pct:.1f}%")
        res_col3.metric("Totalt Mjöl (inkl. surdeg)", f"{total_flour:.0f} g")
        res_col4.metric("Degvikt", f"{total_flour_added + water + starter + salt:.0f} g")
    else:
        st.warning("Lägg till mjöl för att se beräkningarna.")

    st.divider()

    # --- DEL B: DOKUMENTERA RESULTATET ---
    st.subheader("2. Det färdiga brödet")
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        crust_up = st.file_uploader("Bild på skorpan (Valfritt)", type=["jpg", "jpeg", "png"], key="crust_up")
        if crust_up:
            st.session_state.log_crust = crust_up.getvalue()
        if st.session_state.log_crust:
            st.image(compress_image(st.session_state.log_crust), caption="Skorpa", width=200)

    with col_b2:
        crumb_up = st.file_uploader("Bild på inkråmet (Krävs för AI)", type=["jpg", "jpeg", "png"], key="crumb_up")
        if crumb_up:
            st.session_state.log_crumb = crumb_up.getvalue()
        if st.session_state.log_crumb:
            st.image(compress_image(st.session_state.log_crumb), caption="Inkråm", width=200)

    user_rating = st.slider("Ditt betyg på brödet", min_value=1, max_value=5, value=3, help="1 = Bottennapp, 5 = Perfektion")
    tasting_notes = st.text_area("Egna anteckningar", placeholder="T.ex. lite för mörk skorpa, men fantastisk smak.")

    st.divider()

    # --- DEL C: SKICKA TILL BACKEND ---
    if st.button("Spara bak och Kör AI-analys", type="primary"):
        if not st.session_state.log_crumb:
            st.warning("Du måste ladda upp en bild på inkråmet för att kunna logga baket och köra analysen.")
        else:
            with st.spinner("Sparar recept och analyserar inkråmet..."):
                
                # Komprimera bilder
                final_crumb_bytes = compress_image(st.session_state.log_crumb)
                final_crust_bytes = compress_image(st.session_state.log_crust) if st.session_state.log_crust else None
                
                # Bygg payload
                files_payload = {
                    "crumb_image": ("crumb.jpg", final_crumb_bytes, "image/jpeg")
                }
                if final_crust_bytes:
                    files_payload["crust_image"] = ("crust.jpg", final_crust_bytes, "image/jpeg")
                
                # Gör om mjöltabellen till JSON
                flour_json = edited_flours.to_json(orient="records")
                
                data_payload = {
                    "flour_g": int(total_flour_added),
                    "water_g": int(water),
                    "starter_g": int(starter),
                    "salt_g": int(salt),
                    "user_rating": user_rating,
                    "notes": tasting_notes,
                    "flour_details": flour_json
                }
                
                try:
                    # Anropar din NYA endpoint i FastAPI
                    response = requests.post(f"{API_URL}/api/log_bake", files=files_payload, data=data_payload, timeout=45)
                    
                    if response.status_code == 200:
                        result = response.json()
                        ai_data = result.get("ai_result", {})
                        
                        st.success("✅ Baket är loggat och analysen är klar!")
                        
                        # Visa analysresultatet direkt
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            st.subheader(f"Diagnos: {ai_data.get('2_diagnos', 'Klar')}")
                            st.write(ai_data.get('1_visuell_observation', ''))
                        with col_r2:
                            st.subheader("Nästa bak:")
                            for r in ai_data.get('4_rad_for_nasta_bak', []):
                                st.write(f"• {r}")
                        
                        # Rensa formuläret (valfritt, men bra för att inte spara samma sak två ggr)
                        st.session_state.log_crumb = None
                        st.session_state.log_crust = None
                        
                    else:
                        st.error(f"Kunde inte spara baket. Databasen/Backend svarade: {response.text}")
                except requests.exceptions.Timeout:
                    st.error("Det tog för lång tid. Kontrollera din nätverksuppkoppling.")