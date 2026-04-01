import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))

# honestly not sure if we need all of these but better to have more than less
# will trim later if presidio starts being slow
CLINICAL_ALLOWLIST = [
    # units - these kept getting flagged, had to add manually
    "g/dL", "mg/dL", "mg%", "Gms%", "Mill/cumm", "cells/mcL",
    "fL", "pg", "cumm", "Lakh/cumm", "IU/L", "mill/cumm",
    # test names
    "Haemoglobin", "Hemoglobin", "RBC", "WBC", "MCV", "MCH",
    "MCHC", "RDW", "PCV", "Neutrophils", "Lymphocytes",
    "Eosinophils", "Monocytes", "Basophils", "Platelet",
    "Creatinine", "Cholesterol", "Triglycerides", "HDL", "LDL", "VLDL",
    "Haematocrit", "Haematology",

    "Lymphocyte", "Eosinophil", "Monocyte", "Basophil",  # singular variants
    "LDL Cholesterol", "HDL Cholesterol", "VLDL Cholesterol",  # full names
    "Serum Cholesterol", "Serum Creatinine", "Blood Urea",
    "Total Cholesterol",
    # generic words that kept triggering false positives
    "Blood", "Serum", "Differential", "Count", "Profile",
    "Smart", "Mill", "Shah",  # "Mill" was getting flagged as a surname
    "mill/cumm",   # lowercase variant from actual PDF extraction
    "Drlogy",      # lab watermark, not PHI
    "Drlogy.com",  # same
    "Mindray",     # instrument name
    "Caring", "Accurate", "Instant",
    "MD", "Pathologist", "DMLT", "BMLT",
    # instrument names
    # "Mindray",
    
    # page metadata
    "Page",
]

# keywords that boost confidence for phone number detection
PHONE_CONTEXT_KEYWORDS = [
    "ph", "phone", "tel", "mobile", "contact", "call", "fax",
    "collection", "sample", "laboratory", "lab"  # appear near numbers in the given reports
]

PINCODE_CONTEXT_KEYWORDS = [
    "pin", "pincode", "mumbai", "delhi", "bangalore", "hyderabad",
    "chennai", "kolkata", "road", "nagar", "complex", "opposite"
]

ADDRESS_CONTEXT_KEYWORDS = [
    "road", "nagar", "complex", "building", "street", "opposite",
    "near", "plot", "flat", "house", "sector", "colony", "layout"
]
ADDRESS_COMPONENT_KEYWORDS = [
    "Road", "Nagar", "Complex", "Building", "Street", 
    "Colony", "Layout", "Bungalow", "Marg", "Chowk", "Cross",
    "Main", "Phase", "Sector", "Block", "Extension", "Enclave",
    "Lab", "Laboratory", "Hospital", "Clinic", "Centre", "Center"
]

AGE_CONTEXT_KEYWORDS = ["age", "old", "patient", "dob", "born"]

# minimum text length to consider a page as having a proper text layer
# if below this we assume it's a scanned page
MIN_TEXT_LENGTH_PER_PAGE = 50