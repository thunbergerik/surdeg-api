import base64
import os
import json
import requests
import uuid  # <- Ny
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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


@app.get("/")
async def root():
    return {"message": "Surdegs-API är live!"}

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
    


# --- Ny Endpoint för att logga ett komplett bak ---
@app.post("/api/log_bake")
async def log_bake(
    # Filer
    crumb_image: UploadFile = File(...),
    crust_image: UploadFile = File(None), # Gör skorpan valfri
    
    # Recept och metadata som Formulärfält (Form)
    flour_g: int = Form(...),
    water_g: int = Form(...),
    starter_g: int = Form(...),
    salt_g: int = Form(...),
    user_rating: int = Form(...),
    notes: str = Form(""),
    flour_details: str = Form("{}") # Vi skickar mjölsorterna som en JSON-sträng
):
    try:
        # 1. Generera ett unikt ID för detta bak
        bake_id = str(uuid.uuid4())
        
        # 2. Ladda upp bilder till Supabase Storage (om du har satt upp en bucket)
        # Du behöver en funktion för detta, här är pseudokod:
        # crumb_url = await upload_to_supabase_storage("surdeg-images", crumb_image)
        # crust_url = None
        # if crust_image:
        #     crust_url = await upload_to_supabase_storage("surdeg-images", crust_image)
        
        # 3. Skicka inkråmsbilden till OpenAI för analys (Din befintliga funktion)
        image_bytes = await crumb_image.read()
        ai_result = await analyze_crumb_with_openai(image_bytes) # Din befintliga OpenAI-logik
        
        # 4. Spara huvuddatan i din 'bakes'-tabell i Supabase
        bake_data = {
            "id": bake_id,
            "flour_g": flour_g,
            "water_g": water_g,
            "starter_g": starter_g,
            "salt_g": salt_g,
            "user_rating": user_rating,
            "notes": notes,
            "flour_details": json.loads(flour_details), # Konvertera strängen tillbaka till JSON
            # "crust_image_url": crust_url
        }
        # Spara till supabase: supabase.table("bakes").insert(bake_data).execute()

        # 5. Spara analysen i 'crumb_analyses' kopplat till bake_id
        analysis_data = {
            "bake_id": bake_id,
            "ai_analysis": ai_result,
            # "crumb_image_url": crumb_url
        }
        # Spara till supabase: supabase.table("crumb_analyses").insert(analysis_data).execute()

        return {
            "status": "success",
            "bake_id": bake_id,
            "ai_result": ai_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))