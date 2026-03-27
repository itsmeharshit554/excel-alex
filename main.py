from fastapi import FastAPI
from pydantic import BaseModel
import base64
import io
from pprint import pprint
import math

from theExtractPack import extract, prompt

app = FastAPI(title="Extraction API")

class FileRequest(BaseModel):
    name: str
    contentBytes: str

# ✅ Toggle this to enable/disable debug mode
DEBUG_MODE = True


# ✅ Sanitize NaN/Inf → JSON safe
def _sanitize_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(v) for v in obj]

    try:
        if hasattr(obj, "item"):
            return _sanitize_for_json(obj.item())
    except Exception:
        pass

    return obj


@app.get("/")
async def root():
    return {"message": "API is running 🚀"}


@app.post("/extract")
async def extract_data(file: FileRequest):
    try:
        filename = file.name

        # ✅ Decode Base64 → REAL binary
        file_bytes = base64.b64decode(file.contentBytes)

        print("Filename:", filename)
        print("First bytes:", file_bytes[:20])

        if file_bytes[:2] == b'PK':
            print("✅ VALID XLSX")
        else:
            print("❌ STILL INVALID")

        # ✅ Now your original pipeline works
        sorExtData = extract.extractSOR(io.BytesIO(file_bytes))
        bomExtData = extract.extractBOM(io.BytesIO(file_bytes))

        finalData = extract.compileFinalData(bomExtData, sorExtData)

        coreDensity = extract.getDensity(
            finalData.get("coreMaterial"),
            finalData.get("coreMaterialType")
        )
        sleeveDensity = extract.getDensity(
            finalData.get("outerMaterial"),
            finalData.get("outerMaterialType")
        )

        calREM_data = extract.calculate_CoreOD_SleeveID_thick(
            finalData.get("coreLength_mm"),
            finalData.get("outerLength_mm"),
            finalData.get("coreWeight_g"),
            finalData.get("outerWeight_g"),
            finalData.get("coreID_mm"),
            finalData.get("outerSleeveOD_mm"),
            coreDensity,
            sleeveDensity
        )

        finalDataInput = extract.compileFinalData(finalData, calREM_data)
        finalDataInput = _sanitize_for_json(finalDataInput)

        pprint(finalDataInput)

        return {
            "status": "success",
            "filename": filename,
            "extracted_data": finalDataInput
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }