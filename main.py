from fastapi import FastAPI, File, UploadFile
import io
from pprint import pprint
import math  # ✅ ADD

from theExtractPack import extract, prompt

app = FastAPI(title="Extraction API")


# ✅ ADD: convert NaN/Inf into None (JSON null) recursively
def _sanitize_for_json(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(v) for v in obj]

    # handles numpy/pandas scalars without importing numpy
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
async def extract_data(
    rfqFile: UploadFile = File(...)
):
    try:
        filename = rfqFile.filename if rfqFile else ""

        # ✅ Read file once
        file_bytes = await rfqFile.read()

        # ✅ Run extractors
        sorExtData = extract.extractSOR(io.BytesIO(file_bytes))
        bomExtData = extract.extractBOM(io.BytesIO(file_bytes))

        finalData = extract.compileFinalData(
            bomExtData, sorExtData
        )

        # ✅ Core calculations
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

        finalDataInput = extract.compileFinalData(finalData,calREM_data)

        # ✅ ADD: sanitize BEFORE returning response
        finalDataInput = _sanitize_for_json(finalDataInput)
        calREM_data = _sanitize_for_json(calREM_data)

        pprint(finalDataInput)

        # ✅ Generate prompt
        # generatedPrompt = prompt.generatePrompt(
        #     finalDataInput,
        # )

        # ✅ ADD: sanitize prompt too (in case it contains NaN)
        # generatedPrompt = _sanitize_for_json(generatedPrompt)

        return {
            "status": "success",
            "filename": filename,
            "query_params": {
            },
            "extracted_data": finalDataInput
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
