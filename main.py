from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem.Draw import rdMolDraw2D
import google.generativeai as genai  # المكتبة الرسمية الجديدة
import requests
import os

app = FastAPI(title="Kimia Smart PWA API", version="3.5")

# --- إعدادات الأمان (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================

GEMINI_API_KEY = "AIzaSyD4U8tNfP5bQlIKmud9NVq2o2u1Cu4yA6c" 
genai.configure(api_key=GEMINI_API_KEY)
# ==========================================

# --- وظائف مساعدة ---
def get_file_path(filename: str):
    return os.path.join(os.getcwd(), filename)

# --- مسارات تقديم واجهة التطبيق (PWA) ---
@app.get("/", response_class=HTMLResponse)
async def get_index():
    path = get_file_path("index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return f.read()
    return "Error: index.html not found"

@app.get("/manifest.json")
async def get_manifest():
    path = get_file_path("manifest.json")
    return FileResponse(path, media_type="application/json") if os.path.exists(path) else {"error": "not found"}

@app.get("/sw.js")
async def get_sw():
    path = get_file_path("sw.js")
    return FileResponse(path, media_type="application/javascript") if os.path.exists(path) else {"error": "not found"}

# --- مسار البحث عن المركبات ---
class SearchRequest(BaseModel):
    query: str

@app.post("/api/search_compound")
async def search_compound(req: SearchRequest):
    query = req.query.strip()
    url = f"https://cactus.nci.nih.gov/chemical/structure/{query}/smiles"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return {"smiles": response.text.strip(), "found": True}
        return {"error": "لم يتم العثور على المركب", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}

# --- مسار التسمية من PubChem ---
@app.post("/api/name_compound")
async def name_compound(info: dict):
    smiles = info.get("smiles")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/property/IUPACName/JSON"
    response = requests.get(url)
    if response.status_code == 200:
        return {"iupac_name": response.json()["PropertyTable"]["Properties"][0]["IUPACName"]}
    return {"iupac_name": "مركب غير معروف"}

# --- الميزة الابتكارية: البطاقة الذكية باستخدام المكتبة الرسمية الجديدة ---
class SmartCardRequest(BaseModel):
    name: str
    smiles: str

@app.post("/api/smart_card")
def generate_smart_card(req: SmartCardRequest):  # إزالة async هنا لتتوافق مع مكتبة جينشين المتزامنة
    prompt = f"""
    أنت معلم كيمياء جزائري مبدع. قم بإنشاء "بطاقة ذكية" للمركب الكيميائي '{req.name}' (SMILES: {req.smiles}).
    أريد الرد بتنسيق HTML نقي فقط ومباشر (بدون أي علامات markdown مثل ```html).
    يجب أن يحتوي الرد على هذه الأقسام بتنسيق أنيق:
    <h3>🌍 القاموس اللغوي:</h3>
    <ul>
      <li><b>الاسم العلمي (IUPAC):</b> {req.name}</li>
      <li><b>الاسم التجاري الشائع:</b> [اذكر الاسم الشائع]</li>
      <li><b>باللغة الإيطالية 🇮🇹:</b> [الترجمة الإيطالية]</li>
      <li><b>باللغة الفرنسية 🇫🇷:</b> [الترجمة الفرنسية]</li>
    </ul>
    <hr>
    <h3>💡 في حياتنا اليومية:</h3>
    <p>[اشرح أين نجد هذا المركب وما هي استخداماته الشائعة بأسلوب مشوق ومناسب للطلاب]</p>
    <hr>
    <h3>⚠️ خصائص المركب والسلامة:</h3>
    <p>[اذكر خصائصه مثل الحالة الفيزيائية، الرائحة، وهل هو آمن أم خطير]</p>
    """
    try:
        # استخدام طريقتك الرسمية والجديدة تماماً هنا
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # تنظيف النص المستلم وعرضه في واجهة التطبيق
        clean_html = response.text.replace("```html", "").replace("```", "")
        return {"html": clean_html}
    except Exception as e:
        return {"html": f"<p style='color:#e74c3c;'>⚠️ حدث خطأ أثناء توليد البطاقة الذكية: {str(e)}</p>"}
