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
@app.get("/download_mol/")
async def download_mol(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail="صيغة SMILES غير صالحة")
    
    mol_block = Chem.MolToMolBlock(mol)
    return Response(
        content=mol_block, 
        media_type="chemical/x-mdl-molfile", 
        headers={"Content-Disposition": "attachment; filename=molecule.mol"}
    )

@app.get("/", response_class=HTMLResponse)
async def get_interface():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Eco-Synth Agent 🌿</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; display: flex; justify-content: center; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 650px; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; text-align: left; direction: ltr; }
            button { width: 100%; padding: 15px; background: #27ae60; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: 0.3s; }
            button:hover { background: #2ecc71; }
            .visuals { display: flex; align-items: center; justify-content: center; margin-top: 25px; border: 1px solid #eee; padding: 15px; border-radius: 10px; flex-wrap: wrap; gap: 10px; }
            #result { margin-top: 20px; padding: 20px; border-radius: 10px; display: none; line-height: 1.6; }
            .Green { background: #d4edda; color: #155724; } .Yellow { background: #fff3cd; color: #856404; } .Red { background: #f8d7da; color: #721c24; }
            .ai-box { margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.7); border-right: 5px solid #3498db; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="text-align:center; color:#2c3e50;">Eco-Synth Agent 🌿</h2>
            <label>المتفاعلات (SMILES):</label>
            <input type="text" id="reactants" value="CC(=O)O, CCO">
            <label>الناتج المطلوب (SMILES):</label>
            <input type="text" id="product" value="CC(=O)OCC">
            <button onclick="run()">تحليل التفاعل بالذكاء الاصطناعي</button>
            <div id="visuals" class="visuals" style="display:none"></div>
            <div id="result"></div>
        </div>
        <script>
            async function run() {
                const rs = document.getElementById('reactants').value.split(',').map(s => s.trim());
                const p = document.getElementById('product').value.trim();
                const resDiv = document.getElementById('result');
                const visDiv = document.getElementById('visuals');
                resDiv.style.display = "block"; resDiv.className = "Yellow";
                resDiv.innerHTML = "⌛ جاري استشارة الوكيل الذكي...";
                try {
                    const resp = await fetch('/calculate_atom_economy/', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({reactants: rs, desired_product: p})
                    });
                    const d = await resp.json();
                    resDiv.className = d.efficiency_rating;
                    resDiv.innerHTML = `<b>الاقتصاد الذري: ${d.atom_economy_percentage}%</b><br>
                                        <small>المتفاعلات: ${d.total_reactants_weight_g_mol} | الناتج: ${d.product_weight_g_mol}</small>
                                        ${d.ai_suggestion ? '<div class="ai-box">'+d.ai_suggestion+'</div>' : ''}`;
                    visDiv.innerHTML = rs.map(s => `<img src="/render_molecule/?smiles=${encodeURIComponent(s)}">`).join(' + ') + ' ➔ ' + `<img src="/render_molecule/?smiles=${encodeURIComponent(p)}">`;
                    visDiv.style.display = "flex";
                } catch (e) { alert("خطأ في الاتصال"); }
            }
        </script>
    </body>
    </html>
    """