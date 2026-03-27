from pprint import pprint
def generatePrompt(partType, rfqData, l1, l2):
    promptTemplate="""
   Please calculate the costing of the <<PART>> for my part.
 
            Supplier location: <<LOC1>>
 
            Factory location: <<LOC2>>
 
            Parameters of the part:
 
            <<INPUT_PARAMETERS>>
         
    """



    prompt=promptTemplate.replace("<<INPUT_PARAMETERS>>",str(rfqData))
    prompt=prompt.replace("<<LOC1>>",l1)
    prompt=prompt.replace("<<LOC2>>",l2)
    prompt=prompt.replace("<<LOC1>>",l1)
    prompt=prompt.replace("<<PART>>",partType)
    return prompt