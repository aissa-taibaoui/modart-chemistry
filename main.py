import os
import urllib.request
import zipfile
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem.Draw import rdMolDraw2D
import google.generativeai as genai
import requests

app = FastAPI(title="Kimia Pro PWA", version="5.0")

# --- إعدادات الأمان ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- تهيئة مفتاح الذكاء الاصطناعي ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ==========================================
# 🚀 السحر الجديد: تحميل وتثبيت محرك Ketcher الاحترافي تلقائياً
# ==========================================
if not os.path.exists("ketcher"):
    print("جاري تحميل محرك Ketcher الاحترافي للرسم الكيميائي...")
    try:
        url = "[https://github.com/epam/ketcher/releases/download/v2.18.0/ketcher-standalone-2.18.0.zip](https://github.com/epam/ketcher/releases/download/v2.18.0/ketcher-standalone-2.18.0.zip)"
        urllib.request.urlretrieve(url, "ketcher.zip")
        with zipfile.ZipFile("ketcher.zip", 'r') as zip_ref:
            zip_ref.extractall("ketcher")
        os.remove("ketcher.zip")
        print("تم تثبيت لوحة Ketcher بنجاح!")
    except Exception as e:
        print(f"حدث خطأ أثناء تحميل Ketcher: {e}")

# تقديم ملفات لوحة الرسم الجديدة لتعمل ضمن التطبيق
if os.path.exists("ketcher"):
    app.mount("/ketcher", StaticFiles(directory="ketcher", html=True), name="ketcher")
# ==========================================

def get_file_path(filename: str):
    return os.path.join(os.getcwd(), filename)

@app.get("/", response_class=HTMLResponse)
def get_index():
    path = get_file_path("index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return f.read()
    return "Error: index.html not found"

@app.get("/manifest.json")
def get_manifest():
    path = get_file_path("manifest.json")
    return FileResponse(path, media_type="application/json") if os.path.exists(path) else {"error": "not found"}

@app.get("/sw.js")
def get_sw():
    path = get_file_path("sw.js")
    return FileResponse(path, media_type="application/javascript") if os.path.exists(path) else {"error": "not found"}

class SearchRequest(BaseModel):
    query: str

@app.post("/api/search_compound")
def search_compound(req: SearchRequest):
    query = req.query.strip()
    url = f"[https://cactus.nci.nih.gov/chemical/structure/](https://cactus.nci.nih.gov/chemical/structure/){query}/smiles"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return {"smiles": response.text.strip(), "found": True}
        return {"error": "لم يتم العثور على المركب", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}

# التسمية الذكية عبر الذكاء الاصطناعي
@app.post("/api/name_compound")
def name_compound(info: dict):
    smiles = info.get("smiles")
    if not smiles: return {"iupac_name": "مركب غير معروف"}
    prompt = f"""
    بصفتك أستاذ كيمياء خبير يشرح لطلابه، قم بتحليل هذا المركب الكيميائي الممثل بصيغة SMILES: {smiles}
    أريد الرد بتنسيق HTML نقي فقط (بدون markdown).
    <div dir="rtl" style="font-family: 'Tajawal', sans-serif; text-align: right;">
        <div style="font-size: 24px; color: #005088; direction: ltr; text-align: center; margin-bottom: 15px; font-weight: bold; font-family: 'Merriweather', serif;">[اكتب الاسم النظامي IUPAC هنا بالإنجليزية]</div>
        <div style="font-size: 16px; color: #e67e22; margin-bottom: 10px;"><b><i class="fa-solid fa-tag"></i> الاسم الشائع:</b> [الاسم الشائع إن وجد]</div>
        <div style="font-size: 16px; color: #334155; line-height: 1.6; background: #f8fafc; padding: 10px; border-right: 4px solid #11caa0; border-radius: 5px;"><b>💡 قاعدة التسمية:</b> [اشرح بأسلوب أكاديمي الخطوات المتبعة لتسمية هذا المركب]</div>
    </div>
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        # ا
        clean_html = response.text.replace("```html", "").replace("```", "").strip()
        return {"iupac_name": clean_html}
    except:
        return {"iupac_name": "<span style='color:#e74c3c;'>تعذر تحليل المركب.</span>"}

class SmartCardRequest(BaseModel):
    name: str
    smiles: str

@app.post("/api/smart_card")
def generate_smart_card(req: SmartCardRequest):
    if not os.environ.get("GEMINI_API_KEY"):
        return {"html": "<p style='color:#e74c3c;'>⚠️ خطأ: لم يتم إدخال مفتاح الذكاء الاصطناعي.</p>"}
    prompt = f"""
    أنت معلم كيمياء جزائري مبدع. قم بإنشاء "بطاقة ذكية" للمركب الكيميائي '{req.name}' (SMILES: {req.smiles}).
    أريد الرد بتنسيق HTML نقي فقط ومباشر (بدون أي علامات markdown مثل ```html).
    يجب أن يحتوي الرد على هذه الأقسام بتنسيق أنيق:
    <h3>🌍 القاموس اللغوي:</h3>
    <ul><li><b>الاسم العلمي (IUPAC):</b> {req.name}</li><li><b>الاسم التجاري الشائع:</b> [اذكر الاسم الشائع]</li><li><b>باللغة الإيطالية 🇮🇹:</b> [الترجمة الإيطالية]</li><li><b>باللغة الفرنسية 🇫🇷:</b> [الترجمة الفرنسية]</li></ul><hr>
    <h3>💡 في حياتنا اليومية:</h3><p>[اشرح أين نجد هذا المركب وما هي استخداماته الشائعة بأسلوب مشوق ومناسب للطلاب]</p><hr>
    <h3>⚠️ خصائص المركب والسلامة:</h3><p>[اذكر خصائصه مثل الحالة الفيزيائية، الرائحة، وهل هو آمن أم خطير]</p>
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        # تم إصلاح الخطأ البرمجي هنا أيضاً
        clean_html = response.text.replace("```html", "").replace("```", "")
        return {"html": clean_html}
    except Exception as e:
        return {"html": f"<p style='color:#e74c3c;'>⚠️ حدث خطأ: {str(e)}</p>"}
