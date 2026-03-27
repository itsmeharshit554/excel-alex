from fastapi import FastAPI, File, UploadFile
import io
from pprint import pprint

from theExtractPack import extract, prompt

app = FastAPI(title="Extraction API")


@app.get("/")
async def root():
    return {"message": "API is running 🚀"}


@app.post("/extract")
async def extract_data(
    rfqFile: UploadFile = File(...),
    text1: str = "",
    text2: str = "",
    partType: str = "Outer Sleeve",
):
    try:
        filename = rfqFile.filename if rfqFile else ""

        # ✅ Read file once
        file_bytes = await rfqFile.read()

        # ✅ Run extractors
        sorExtData = extract.extractSOR(io.BytesIO(file_bytes))
        bomExtData = extract.extractBOM(io.BytesIO(file_bytes))
        imgExtData = extract.extractImg(
            io.BytesIO(file_bytes),
            sorExtData.get("outerSleeveOD_mm")
        )

        finalData = extract.compileFinalData(
            imgExtData, bomExtData, sorExtData
        )

        # ✅ Core calculations
        coreDensity = extract.getDensity(
            finalData.get("coreMaterial"),
            finalData.get("coreMaterialType")
        )

        coreOD = extract.getCoreOD(
            coreDensity,
            finalData.get("coreLength_mm"),
            finalData.get("coreID_mm"),
            finalData.get("coreWeight_g")
        )

        tempDict = {
            "coreDensity_g/mm3": coreDensity,
            "coreOD_mm": coreOD
        }

        finalDataInput = extract.compileFinalData(finalData, tempDict)

        pprint(finalDataInput)

        # ✅ Generate prompt
        generatedPrompt = prompt.generatePrompt(
            partType,
            finalDataInput,
            text1,
            text2
        )

        return {
            "status": "success",
            "filename": filename,
            "query_params": {
                "text1": text1,
                "text2": text2,
                "partType": partType
            },
            "extracted_data": finalDataInput,
            "generated_prompt": generatedPrompt
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }