from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem.Draw import rdMolDraw2D
import asyncio
import json
import urllib.request
import urllib.error
import requests
import os

app = FastAPI(title="Kimia Smart API", version="2.0")

# --- إعدادات الأمان (CORS) لضمان عمل PWA و PWABuilder ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 👇👇👇 ضع مفتاح Gemini الخاص بك هنا 👇👇👇
GOOGLE_API_KEY = "ضـع_مفـتاحك_هنا" 
# ==========================================

# --- وظائف مساعدة لنظام الملفات ---
def get_file_path(filename: str):
    return os.path.join(os.getcwd(), filename)

def get_molecular_weight(smiles_string: str) -> float:
    mol = Chem.MolFromSmiles(smiles_string)
    if mol is None:
        raise HTTPException(status_code=400, detail="صيغة SMILES غير صالحة")
    return Descriptors.ExactMolWt(mol)

# --- محرك الذكاء الاصطناعي (نظام التبديل التلقائي) ---
async def get_ai_green_suggestion(reactants: List[str], product: str, economy: float) -> str:
    prompt = f"أنت خبير كيمياء خضراء. حلل التفاعل: المتفاعلات {reactants} والناتج {product} واقتصاده الذري {economy}%. اقترح تحسيناً بالعربية (HTML)."
    clean_key = GOOGLE_API_KEY.strip()
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # النماذج المكتشفة في جهازك لعام 2026
    models = [
        "models/gemini-3.1-flash-image-preview",
        "models/gemini-3-pro-image-preview",
        "models/gemini-2.5-computer-use-preview-10-2025"
    ]
    
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={clean_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            response = await asyncio.to_thread(urllib.request.urlopen, req)
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except:
            continue
    return "⚠️ جميع نماذج الذكاء الاصطناعي مشغولة حالياً."

# --- المسارات (Endpoints) لتقديم ملفات التطبيق (PWA) ---

@app.get("/", response_class=HTMLResponse)
async def get_index():
    path = get_file_path("index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Error: index.html not found"

@app.get("/manifest.json")
async def get_manifest():
    path = get_file_path("manifest.json")
    return FileResponse(path, media_type="application/json") if os.path.exists(path) else {"error": "not found"}

@app.get("/sw.js")
async def get_sw():
    path = get_file_path("sw.js")
    return FileResponse(path, media_type="application/javascript") if os.path.exists(path) else {"error": "not found"}

# --- المسارات البرمجية (API) لخدمات Kimia الذكية ---

@app.post("/api/name_compound")
async def name_compound(info: dict):
    smiles = info.get("smiles")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/property/IUPACName/JSON"
    response = requests.get(url)
    if response.status_code == 200:
        name = response.json()["PropertyTable"]["Properties"][0]["IUPACName"]
        return {"iupac_name": name}
    return {"iupac_name": "مركب غير معروف"}

@app.get("/render_molecule/")
async def render_molecule(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: return Response(content="<svg></svg>", media_type="image/svg+xml")
    drawer = rdMolDraw2D.MolDraw2DSVG(300, 200)
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return Response(content=drawer.GetDrawingText(), media_type="image/svg+xml")

@app.get("/download_mol/")
async def download_mol(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None: raise HTTPException(status_code=400, detail="Invalid SMILES")
    return Response(content=Chem.MolToMolBlock(mol), media_type="chemical/x-mdl-molfile", 
                    headers={"Content-Disposition": "attachment; filename=molecule.mol"})

class ReactionInput(BaseModel):
    reactants: List[str]
    desired_product: str

@app.post("/calculate_atom_economy/")
async def calculate_atom_economy(reaction: ReactionInput):
    try:
        mw_r = sum([get_molecular_weight(r) for r in reaction.reactants])
        mw_p = get_molecular_weight(reaction.desired_product)
        economy = (mw_p / mw_r) * 100
        rating = "Green" if economy >= 80 else "Yellow" if economy >= 50 else "Red"
        suggestion = await get_ai_green_suggestion(reaction.reactants, reaction.desired_product, round(economy, 2)) if economy < 85 else ""
        return {
            "atom_economy": round(economy, 2),
            "rating": rating,
            "ai_suggestion": suggestion
        }
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))