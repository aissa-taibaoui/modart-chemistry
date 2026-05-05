from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# --- إضافة تصريح الدخول الأمني (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يسمح لأي موقع (مثل PWABuilder) بقراءة الملفات
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------

def get_file_path(filename: str):
    return os.path.join(os.getcwd(), filename)

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
    if os.path.exists(path):
        return FileResponse(path, media_type="application/json")
    return {"error": "manifest.json not found"}

@app.get("/sw.js")
async def get_sw():
    path = get_file_path("sw.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript")
    return {"error": "sw.js not found"}

@app.post("/api/name_compound")
async def name_compound(info: dict):
    smiles = info.get("smiles")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/property/IUPACName/JSON"
    response = requests.get(url)
    if response.status_code == 200:
        name = response.json()["PropertyTable"]["Properties"][0]["IUPACName"]
        return {"iupac_name": name}
    return {"iupac_name": "مركب غير معروف"}
import requests
from pydantic import BaseModel

# نموذج استقبال البيانات للبحث
class SearchRequest(BaseModel):
    query: str

@app.post("/api/search_compound")
async def search_compound(req: SearchRequest):
    query = req.query.strip()
    
    # محاولة جلب كود SMILES من قاعدة PubChem بناءً على الاسم المكتوب
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/property/CanonicalSMILES/JSON"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            smiles = data['PropertyTable']['Properties'][0]['CanonicalSMILES']
            return {"smiles": smiles, "found": True}
        else:
            return {"error": "لم يتم العثور على المركب", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}
        @app.post("/api/search_compound")
async def search_compound(req: SearchRequest):
    query = req.query.strip()
    
    # استخدام قاعدة بيانات NCI Cactus بدلاً من PubChem لتجنب الحظر
    url = f"https://cactus.nci.nih.gov/chemical/structure/{query}/smiles"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            smiles = response.text.strip()
            return {"smiles": smiles, "found": True}
        else:
            return {"error": "لم يتم العثور على المركب", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}
