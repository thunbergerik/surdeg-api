@app.get("/")
async def root():
    return {"message": "Surdegs-API är live!"}

import base64
import os
import json
import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

# Ladda miljövariabler
load_dotenv()

# Sätt upp OpenAI
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Hämta Supabase-variablerna
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

app = FastAPI(title="Surdeg Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """
Du är en analytisk master bagare specialiserad på surdeg och bakkemi. 
Din uppgift är att analysera bilder på surdegsbröds inkråm (crumb structure) med extrem noggrannhet.

Här är dina diagnostiska riktlinjer:
- "Underjäst": Kännetecknas av "tunneling". Stora, oregelbundna luftbubblor kombinerat med ett väldigt kompakt, tätt inkråm.
- "Överjäst": Kännetecknas av brist på spänst. Ett väldigt jämnt, tätt inkråm med övervägande små hål överallt.
- "Perfekt jäst": Kännetecknas av "wild crumb". En pärlbandsliknande, vacker distribution av stora och små hål jämnt fördelade.
- "Formningsfel": Stora hål som uppenbart är stora inneslutna luftfickor från när degen veks.

Du MÅSTE svara i JSON-format med exakt denna ordning och struktur:
{
  "1_visuell_observation": "Beskriv exakt vad du ser i bilden.",
  "2_diagnos": "Välj EN: Perfekt jäst, Underjäst, Överjäst, Formningsfel",
  "3_teknisk_forklaring": "Kemisk/biologisk orsak.",
  "4_rad_for_nasta_bak": ["Råd 1", "Råd 2"],
  "5_konfidens_score": 85
}
"""

@app.post("/api/analyze")
async def analyze_crumb(file: UploadFile = File(...)):
    # 1. Koda bilden
    file_bytes = await file.read()
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    
    # 2. Skicka till OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analysera detta inkråm."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ],
            }
        ],
        response_format={ "type": "json_object" }
    )
    
    # 3. Läs AI:ns svar som JSON
    ai_response_json = json.loads(response.choices[0].message.content)
    
    # 4. Spara i Supabase via ett direkt REST API-anrop!
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # Vi skickar datan till tabellen "crumb_analyses"
    endpoint = f"{SUPABASE_URL}/rest/v1/crumb_analyses"
    
    # Data-payloaden (kolumnnamn : värde)
    data = {
        "ai_analysis": ai_response_json
    }
    
    # Utför POST-anropet
    db_response = requests.post(endpoint, headers=headers, json=data)
    
    # Skriver ut i terminalen om det gick bra eller dåligt
    if db_response.status_code == 201:
        print("✅ Analysen är sparad i databasen!")
    else:
        print(f"❌ Något gick fel med databasen: {db_response.text}")

    # 5. Returnera till användaren
    return ai_response_json

@app.get("/api/history")
async def get_history():
    # Samma headers som förut, men vi behöver inte Content-Type för en GET-fråga
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # Vi säger till Supabase: 
    # 1. select=* (Hämta all data)
    # 2. order=created_at.desc (Sortera med nyaste datumet först)
    endpoint = f"{SUPABASE_URL}/rest/v1/crumb_analyses?select=*&order=created_at.desc"
    
    db_response = requests.get(endpoint, headers=headers)
    
    if db_response.status_code == 200:
        # Om allt går bra, skicka tillbaka listan med analyser
        return db_response.json()
    else:
        # Om något strular, berätta vad
        return {"error": "Kunde inte hämta historiken", "details": db_response.text}