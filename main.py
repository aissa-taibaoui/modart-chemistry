from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem.Draw import rdMolDraw2D
import google.generativeai as genai
import requests
import os

app = FastAPI(title="Kimia Smart PWA API", version="3.6")

# --- إعدادات الأمان (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🔒 حماية برمجية: قراءة المفتاح سرياً من إعدادات Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
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

# --- مسار التسمية الذكي بالذكاء الاصطناعي ---
@app.post("/api/name_compound")
def name_compound(info: dict):
    smiles = info.get("smiles")
    if not smiles:
        return {"iupac_name": "مركب غير معروف"}

    prompt = f"""
    بصفتك أستاذ كيمياء خبير يشرح لطلابه، قم بتحليل هذا المركب الكيميائي الممثل بصيغة SMILES: {smiles}
    أريد الرد بتنسيق HTML نقي فقط (بدون أي علامات markdown مثل ```html).
    يجب أن يكون الرد بهذا الشكل الأنيق:
    <div dir="rtl" style="font-family: 'Tajawal', sans-serif; text-align: right;">
        <div style="font-size: 24px; color: #005088; direction: ltr; text-align: center; margin-bottom: 15px; font-weight: bold; font-family: 'Merriweather', serif;">[اكتب الاسم النظامي IUPAC هنا بالإنجليزية]</div>
        <div style="font-size: 16px; color: #e67e22; margin-bottom: 10px;"><b><i class="fa-solid fa-tag"></i> الاسم الشائع:</b> [اكتب الاسم الشائع إن وجد]</div>
        <div style="font-size: 16px; color: #334155; line-height: 1.6; background: #f8fafc; padding: 10px; border-right: 4px solid #11caa0; border-radius: 5px;"><b>💡 قاعدة التسمية:</b> [اشرح باختصار شديد وبأسلوب أكاديمي الخطوات المتبعة لتسمية هذا المركب (مثل السلسلة الرئيسية، الترقيم، المجموعات الوظيفية) لتوضيحها للمتعلم]</div>
    </div>
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        clean_html = response.text.replace("```html", "").replace("```", "").strip()
        return {"iupac_name": clean_html}
    except Exception as e:
        # نظام طوارئ: العودة إلى PubChem إذا كان هناك ضغط على خوادم الذكاء الاصطناعي
        url = f"[https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/](https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/){smiles}/property/IUPACName/JSON"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                name = res.json()["PropertyTable"]["Properties"][0]["IUPACName"]
                return {"iupac_name": f"<div style='direction:ltr; text-align:center; font-weight:bold; font-size:22px;'>{name}</div>"}
        except:
            pass
        return {"iupac_name": "<span style='color:#e74c3c;'>تعذر تحليل المركب.</span>"}
# --- البطاقة الذكية بالذكاء الاصطناعي ---
class SmartCardRequest(BaseModel):
    name: str
    smiles: str

@app.post("/api/smart_card")
def generate_smart_card(req: SmartCardRequest):
    if not os.environ.get("GEMINI_API_KEY"):
        return {"html": "<p style='color:#e74c3c;'>⚠️ خطأ: لم يتم إدخال مفتاح الذكاء الاصطناعي في إعدادات Render بعد.</p>"}

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
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        clean_html = response.text.replace("```html", "").replace("```", "")
        return {"html": clean_html}
    except Exception as e:
        return {"html": f"<p style='color:#e74c3c;'>⚠️ حدث خطأ أثناء توليد البطاقة الذكية: {str(e)}</p>"}
@app.post("/api/analyze_reaction")
def analyze_reaction(info: dict):
    reaction_smiles = info.get("smiles", "")
    
    # التحقق مما إذا كان الرسم تفاعلاً (يحتوي على علامة >>)
    if ">>" not in reaction_smiles:
        return {"error": "الرجاء رسم تفاعل كيميائي باستخدام أداة السهم."}
        
    reactants_smiles, products_smiles = reaction_smiles.split(">>")
    
    # دالة مساعدة لاستخراج الكتلة والصيغة
    def get_mol_data(smiles_str):
        data = []
        for s in smiles_str.split("."): # فصل المركبات بالنقاط
            mol = Chem.MolFromSmiles(s)
            if mol:
                data.append({
                    "smiles": s,
                    "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
                    "mw": round(Descriptors.ExactMolWt(mol), 2)
                })
        return data

    return {
        "reactants": get_mol_data(reactants_smiles),
        "products": get_mol_data(products_smiles)
    }
