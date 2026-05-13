import base64
import os
import json
import uuid
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
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
- "Underjäst": Kännetecknas av "tunneling". Stora, oregelbundna luftbubblor kombinerat med ett väldigt kompakt, tätt inkråm i botten.
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

@app.get("/")
async def root():
    return {"message": "Surdegs-API är live och redo att baka!"}

@app.post("/api/analyze")
async def analyze_crumb(file: UploadFile = File(...)):
    # 1. Koda bilden till Base64
    file_bytes = await file.read()
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    
    # 2. Skicka till OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini", # eller gpt-4o om du vill ha den större modellen
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
    
    # 3. Formatera resultatet
    ai_response_json = json.loads(response.choices[0].message.content)
    
    # 4. Spara i Supabase
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    endpoint = f"{SUPABASE_URL}/rest/v1/crumb_analyses"
    data = {"ai_analysis": ai_response_json}
    requests.post(endpoint, headers=headers, json=data)
    
    return ai_response_json

@app.post("/api/log_bake")
async def log_bake(
    crumb_image: UploadFile = File(...),
    crust_image: UploadFile = File(None), # Valfri fil
    flour_g: int = Form(...),
    water_g: int = Form(...),
    starter_g: int = Form(...),
    salt_g: int = Form(...),
    user_rating: int = Form(...),
    notes: str = Form(""),
    flour_details: str = Form("{}")
):
    try:
        # 1. Skapa ett unikt ID för hela baket
        bake_id = str(uuid.uuid4())
        
        # 2. Analysera inkråmet med OpenAI
        file_bytes = await crumb_image.read()
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        ai_response = client.chat.completions.create(
            model="gpt-4o", # Använder den stora modellen för bäst precision på sparade bak
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analysera detta inkråm för min loggbok."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                    ],
                }
            ],
            response_format={ "type": "json_object" }
        )
        ai_response_json = json.loads(ai_response.choices[0].message.content)
        
        # 3. Förbered anrop till Supabase REST API
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        # 4. Spara Receptet (Tabell: bakes)
        bake_data = {
            "id": bake_id,
            "flour_g": flour_g,
            "water_g": water_g,
            "starter_g": starter_g,
            "salt_g": salt_g,
            "user_rating": user_rating,
            "notes": notes,
            "flour_details": json.loads(flour_details) # Sträng till JSON
        }
        bake_endpoint = f"{SUPABASE_URL}/rest/v1/bakes"
        bake_req = requests.post(bake_endpoint, headers=headers, json=bake_data)
        
        if bake_req.status_code not in [200, 201]:
            raise Exception(f"Kunde inte spara recept: {bake_req.text}")

        # 5. Spara Analysen och koppla till Receptet (Tabell: crumb_analyses)
        analysis_data = {
            "bake_id": bake_id, # Länken till receptet!
            "ai_analysis": ai_response_json
        }
        analysis_endpoint = f"{SUPABASE_URL}/rest/v1/crumb_analyses"
        requests.post(analysis_endpoint, headers=headers, json=analysis_data)
        
        # Returnera svaret till Streamlit
        return {
            "status": "success",
            "bake_id": bake_id,
            "ai_result": ai_response_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    # Hämtar alla analyser sorterade på nyast först
    endpoint = f"{SUPABASE_URL}/rest/v1/crumb_analyses?select=*&order=created_at.desc"
    
    db_response = requests.get(endpoint, headers=headers)
    
    if db_response.status_code == 200:
        return db_response.json()
    else:
        return {"error": "Kunde inte hämta historiken", "details": db_response.text}