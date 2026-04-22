from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse  # استدعاء أداة عرض الملفات
from pydantic import BaseModel
import requests

app = FastAPI(title="Organic Compound Naming API")

class CompoundInput(BaseModel):
    smiles: str

# --------------------------------------------------
# المسار الجديد: جعل الخادم يعرض واجهة التطبيق
# --------------------------------------------------
@app.get("/")
def serve_frontend():
    # سيقوم الخادم بالبحث عن ملف index.html في نفس المجلد وعرضه
    return FileResponse("index.html")

# --------------------------------------------------
# محرك الكيمياء
# --------------------------------------------------
def get_iupac_name(smiles_code: str) -> str:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles_code}/property/IUPACName/JSON"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['PropertyTable']['Properties'][0]['IUPACName']
        else:
            return "لم يتم التعرف على المركب"
    except Exception as e:
        return "حدث خطأ في الاتصال بقاعدة البيانات"

@app.post("/api/name_compound")
def name_compound(compound: CompoundInput):
    if not compound.smiles:
        raise HTTPException(status_code=400, detail="Please provide a valid SMILES string.")
    
    iupac_name = get_iupac_name(compound.smiles)
    
    return {
        "input_smiles": compound.smiles,
        "iupac_name": iupac_name,
        "status": "success"
    }