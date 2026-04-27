from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import requests
import os

app = FastAPI()

# دالة للتأكد من وجود الملف قبل إرساله (لتجنب الـ Not Found)
def get_file_path(filename: str):
    # يبحث في المجلد الحالي
    return os.path.join(os.getcwd(), filename)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    path = get_file_path("index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Error: index.html not found in root directory"

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