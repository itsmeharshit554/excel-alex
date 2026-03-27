from openpyxl import load_workbook
from io import BytesIO
import re
import pandas as pd
import math

def to_float(value, mode="first"):
    import re

    if isinstance(value, (int, float)):
        return float(value)

    nums = re.findall(r'\d+(?:\.\d+)?', str(value))
    nums = [float(n) for n in nums]

    if not nums:
        raise ValueError(f"No numeric value found in: {value}")

    if mode == "max":
        return max(nums)
    elif mode == "min":
        return min(nums)
    else:
        return nums[0]
    

def extractLen(text):
    nums = re.findall(r'\d+(?:\.\d+)?', text)
    nums = [float(n) for n in nums]
    return min(nums) if nums else None

def normalize_dimension_text(text):
    text = text.strip().replace(" ", "")

        # Normalize common OCR mistakes
    text = text.replace("Ø", "d")
    text = re.sub(r'^[80]=', 'd=', text)     # 8= / 0= → d=
    text = re.sub(r'^6=', 't=', text)        # 6= → t=
    text = re.sub(r'^4=', 'A=', text)        # 4= → A=

        # Normalize units
    text = text.replace("mm2", "mm²")
    text = text.replace("m㎡", "mm²")
    return text

def find_section_row(df, text):
    for r in range(df.shape[0]):
        if df.iloc[r].astype(str).str.contains(text, case=False, na=False).any():
            return r
    return None

def calculate_CoreOD_SleeveID_thick(CoreLen, SleeveLen, CoreWeight, SleeveWeight, CoreID, SleeveOD, coreDensity, sleeveDensity):
    CoreLen = to_float(CoreLen,mode="max")
    SleeveLen = to_float(SleeveLen,mode="max")
    CoreWeight = float(CoreWeight)
    SleeveWeight = float(SleeveWeight)
    CoreID = to_float(CoreID,mode="max")
    SleeveOD = to_float(SleeveOD,mode="max")
    coreDensity = float(coreDensity)
    sleeveDensity = float(sleeveDensity)

    coreVol = CoreWeight / coreDensity
    sleeveVol = SleeveWeight / sleeveDensity

    CoreOD = math.sqrt((4 * coreVol) / (3.14 * CoreLen) + (CoreID ** 2))
    SleeveID = math.sqrt((SleeveOD ** 2) - ((4 * sleeveVol) / (3.14 * SleeveLen)))
    thickness = (SleeveOD - SleeveID) / 2

    return {
        "CoreOD": round(CoreOD,2),
        "CoreID": round(CoreID,2),
        "thickness": round(thickness,2)
    }
    

def findContent(df, anchor_value):
    mask = df == anchor_value
    locations = mask.stack()[mask.stack()].index.tolist()

    if locations:
        # Get the first occurrence (row_index, col_index)
        row_idx, col_idx = locations[0]
        column_remainder = df.iloc[row_idx + 1:, col_idx]
        seriesFinal = column_remainder.reset_index(drop=True)
        
        print(f"Found value at Row {row_idx}, Column {col_idx}")
        print("Data following the value:")
        print(seriesFinal)
        return seriesFinal
    else:
        print(f"Value '{anchor_value}' not found anywhere in the file.")

def prepareDfSOR(s1,s2,s3):
    finalDf=pd.concat([s1,s2,s3], axis=1)
    finalDf.columns = [1, 2, 3]
    finalDf.at[findRow(finalDf,"Min. contact area for core"),2]="Not available"
    finalDf=finalDf.dropna(subset=[2, 3], thresh=1)
    finalDf=finalDf.loc[:finalDf.astype(str)
              .apply(lambda c: c.str.contains("Static Stiffnesses", na=False))
              .any(axis=1)
              .idxmax()]
    return finalDf

def prepareDfBOM(s1,s2,s3,s4,s5,s6,s7):
    finalDf=pd.concat([s1,s2,s3,s4,s5,s6,s7], axis=1)
    finalDf.columns = [1, 2, 3, 4, 5, 6, 7]
    finalDf=finalDf.dropna(subset=[1 ,2, 3, 4, 5, 6, 7], thresh=1)
    finalDf=finalDf.loc[:finalDf.astype(str)
              .apply(lambda c: c.str.contains("Total", na=False))
              .any(axis=1)
              .idxmax()]
    return finalDf

def findRow(df,text):
    row= df.index[df[1] == text][0]
    return row

def find2Row(df, text):
    rows = df.index[df[1] == text]
    return rows[1] if len(rows) > 1 else None

def splitAreaBOM(area):
    core_text  = area["coreArea"]
    outer_text = area["outerArea"]
        
    core_text = core_text.split("\n")
    outer_text = outer_text.split("\n")

    return {
    "coreBondingArea":core_text[0].split(":")[1].strip(),
    "corePrepArea":core_text[1].split(":")[1].strip(),
    "outerBondingArea":outer_text[0].split(":")[1].strip(),
    "outerPrepArea":outer_text[1].split(":")[1].strip()
    }

def extractBOM(filename):
    df=pd.read_excel(filename, sheet_name="7.BOM", header=None, dtype=str)
    print(df)

    col1=findContent(df,"Name")
    col2=findContent(df,"Reference\nnumber and index")
    col3=findContent(df,"Material")
    col4=findContent(df,"Manufacturing Process")
    col5=findContent(df,"Surface Preparation")
    col6=findContent(df,"Qty.")
    col7=findContent(df,"Calculated weight (g)")

    finalDf=prepareDfBOM(col1,col2,col3,col4,col5,col6,col7)
    print(finalDf)
    finalDict={
        "coreName":finalDf.at[findRow(finalDf,"Core"),2],
        "outerName":finalDf.at[findRow(finalDf,"Outer Sleeve"),2],
        "rubberName":finalDf.at[findRow(finalDf,"Rubber"),2],
        "coreMaterialType":finalDf.at[findRow(finalDf,"Core"),3],
        "outerMaterialType":finalDf.at[findRow(finalDf,"Outer Sleeve"),3],
        "rubberMaterial":finalDf.at[findRow(finalDf,"Rubber"),3],
        "coreProcess":finalDf.at[findRow(finalDf,"Core"),4],
        "outerProcess":finalDf.at[findRow(finalDf,"Outer Sleeve"),4],
        "rubberProcess":finalDf.at[findRow(finalDf,"Rubber"),4],
        "coreSurface":finalDf.at[findRow(finalDf,"Core"),5],
        "outerSurface":finalDf.at[findRow(finalDf,"Outer Sleeve"),5],
        "rubberSurface":finalDf.at[findRow(finalDf,"Rubber"),5],
        "coreQty":finalDf.at[findRow(finalDf,"Core"),6],
        "outerQty":finalDf.at[findRow(finalDf,"Outer Sleeve"),6],
        "rubberQty":finalDf.at[findRow(finalDf,"Rubber"),6],
        "coreWeight_g":finalDf.at[findRow(finalDf,"Core"),7],
        "outerWeight_g":finalDf.at[findRow(finalDf,"Outer Sleeve"),7],
        "rubberWeight_g":finalDf.at[findRow(finalDf,"Rubber"),7]
    }
    tempArea={
        "coreArea":finalDf.at[find2Row(finalDf,"Core"),2],
        "outerArea":finalDf.at[find2Row(finalDf,"Outer Sleeve"),2]
    }
    tempArea = splitAreaBOM(tempArea)
    finalDict=finalDict | tempArea
    print(finalDict)

    return finalDict
    

def extractSOR(filename):
    df=pd.read_excel(filename, sheet_name="6. PC1_Bushing_SOR", header=None, dtype=str)
    print(df)
    
    col1 = findContent(df, "Feature")
    col2 = findContent(df, "Customer requirement \n(filled out by AE)")
    col3 = findContent(df, "VC Design\n(filled out by ProdE)")
    finalDf=prepareDfSOR(col1,col2,col3)   
    print(finalDf)

    finalDict={
        "coreName":finalDf.at[findRow(finalDf,"Avgerage part volume p. a."),2],
        "outerSleeveOD_mm":finalDf.at[findRow(finalDf,"Bush OD (delivery condition)"),3],
        "outerLength_mm": finalDf.at[findRow(finalDf,"Outer sleeve length"),3],
        "coreLength_mm": finalDf.at[findRow(finalDf,"Core length"),2],
        "coreID_mm": finalDf.at[findRow(finalDf,"Core ID"),3],
        "clampingForce_KN":finalDf.at[findRow(finalDf,"Clamping force"),2],
        "permanentSetAllowed":finalDf.at[findRow(finalDf,"Permanent set allowed"),2],
        "minContactAreaCore_mm2":finalDf.at[findRow(finalDf,"Min. contact area for core"),2],
        "coreMaterial":finalDf.at[findRow(finalDf,"Core - material"),2],
        "outerMaterial":finalDf.at[findRow(finalDf,"Outer sleeve - material"),2]
    }
    print(finalDict)
    return finalDict
def getDensity(material, materialType):
    if '6063' in (material or materialType):
        return 0.00270
    elif '6060' in(material or materialType):
        return 0.00271
    elif '6005A' in (material or materialType):
        return 0.00271
    elif '6060' in (material or materialType):
        return 0.00271
    elif '6005A' in (material or materialType):
        return 0.00271
    elif '6061' in (material or materialType):
        return 0.00270
    elif '6082' in (material or materialType):
        return 0.00271
    elif '7075' in (material or materialType):
        return 	0.00281
    elif 'steel' in (material.lower() or materialType.lower()):
        return 0.00785
    else:
        return 0.00270

def getCoreOD(density, coreLength, coreID ,weight):
    coreLength=extractLen(coreLength)
    volume=float(weight)/density
    coreOD=math.sqrt(((4*volume)/(3.14*coreLength)+(float(coreID)**2)))
    return round(coreOD,2)

def compileFinalData(*args):
    finalData = {}
    for data in args:
        finalData.update(data)
    return finalData

