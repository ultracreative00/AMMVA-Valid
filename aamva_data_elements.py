"""
AAMVA DL/ID Card Design Standard — Complete Data Element Catalog
Covers AAMVA Standard Versions 1 through 10 (2000-2025)
Annex B: Data Element Definitions
Annex E: Vehicle Class / Restriction / Endorsement codes
Annex F: Jurisdiction-specific elements

Element entry format:
  element_id -> {
    "label": human-readable name,
    "type": "A"=alpha, "N"=numeric, "AN"=alphanumeric, "D"=date, "B"=boolean,
    "min": minimum length (characters),
    "max": maximum length (characters),
    "presence": "M"=mandatory, "O"=optional, "MIF"=mandatory if feature present,
    "version_added": AAMVA version when element was introduced,
    "subfile": which subfile(s) this element belongs to,
    "desc": short description,
  }
"""

ELEMENT_CATALOG = {
    # ── HEADER / SUBFILE DIRECTORY (Annex D) ──────────────────────────────────
    # Parsed separately from the header, not as named elements

    # ── MANDATORY DL/ID ELEMENTS (Annex B, all versions) ─────────────────────
    "DCA": {"label": "Jurisdiction-Specific Vehicle Class",  "type": "AN", "min": 1,  "max": 6,  "presence": "M", "version_added": 1, "subfile": "DL",    "desc": "Jurisdiction-specific vehicle class / group code"},
    "DCB": {"label": "Jurisdiction-Specific Restriction Codes", "type": "AN", "min": 0, "max": 12, "presence": "M", "version_added": 1, "subfile": "DL",    "desc": "Restriction codes (comma-separated for multiple)"},
    "DCD": {"label": "Jurisdiction-Specific Endorsement Codes", "type": "AN", "min": 0, "max": 5,  "presence": "M", "version_added": 1, "subfile": "DL",    "desc": "Endorsement codes (comma-separated for multiple)"},
    "DBA": {"label": "Document Expiration Date",              "type": "D",  "min": 8,  "max": 8,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Date document expires"},
    "DCS": {"label": "Customer Family Name",                  "type": "AN", "min": 1,  "max": 40, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Family (last) name of card holder"},
    "DAC": {"label": "Customer First Name",                   "type": "AN", "min": 1,  "max": 40, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "First name of card holder"},
    "DAD": {"label": "Customer Middle Name(s)",               "type": "AN", "min": 0,  "max": 40, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Middle name(s) or initial"},
    "DBD": {"label": "Document Issue Date",                   "type": "D",  "min": 8,  "max": 8,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Date document was issued"},
    "DBB": {"label": "Date of Birth",                         "type": "D",  "min": 8,  "max": 8,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Customer date of birth"},
    "DBC": {"label": "Physical Description — Sex",            "type": "N",  "min": 1,  "max": 1,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "1=Male, 2=Female, 9=Not Specified"},
    "DAY": {"label": "Physical Description — Eye Color",      "type": "A",  "min": 3,  "max": 3,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "BLK BLU BRN GRY GRN HAZ MAR PNK DIC UNK"},
    "DAU": {"label": "Physical Description — Height",         "type": "AN", "min": 6,  "max": 6,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "nnnIN (inches) or nnnCM (centimetres)"},
    "DAG": {"label": "Address — Street 1",                    "type": "AN", "min": 1,  "max": 35, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Street address line 1"},
    "DAH": {"label": "Address — Street 2",                    "type": "AN", "min": 0,  "max": 35, "presence": "O", "version_added": 1, "subfile": "DL/ID", "desc": "Street address line 2"},
    "DAI": {"label": "Address — City",                        "type": "AN", "min": 1,  "max": 20, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "City"},
    "DAJ": {"label": "Address — Jurisdiction Code",           "type": "A",  "min": 2,  "max": 2,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "State/Province/Territory abbreviation"},
    "DAK": {"label": "Address — Postal Code",                 "type": "AN", "min": 9,  "max": 11, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "5+4 US ZIP or Canadian postal code"},
    "DAQ": {"label": "Customer ID Number",                    "type": "AN", "min": 1,  "max": 25, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Jurisdiction-unique DL/ID number"},
    "DCF": {"label": "Document Discriminator",                "type": "AN", "min": 4,  "max": 25, "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "Unique document number within a series"},
    "DCG": {"label": "Country Identification",                "type": "A",  "min": 3,  "max": 3,  "presence": "M", "version_added": 1, "subfile": "DL/ID", "desc": "USA, CAN, or MEX"},
    "DDE": {"label": "Family Name Truncation",                "type": "A",  "min": 1,  "max": 1,  "presence": "M", "version_added": 4, "subfile": "DL/ID", "desc": "T=Truncated, N=Not truncated, U=Unknown"},
    "DDF": {"label": "First Name Truncation",                 "type": "A",  "min": 1,  "max": 1,  "presence": "M", "version_added": 4, "subfile": "DL/ID", "desc": "T=Truncated, N=Not truncated, U=Unknown"},
    "DDG": {"label": "Middle Name Truncation",                "type": "A",  "min": 1,  "max": 1,  "presence": "M", "version_added": 4, "subfile": "DL/ID", "desc": "T=Truncated, N=Not truncated, U=Unknown"},

    # ── OPTIONAL PERSONAL ELEMENTS ────────────────────────────────────────────
    "DAZ": {"label": "Hair Color",                            "type": "A",  "min": 3,  "max": 12, "presence": "O", "version_added": 1, "subfile": "DL/ID", "desc": "BAL BLK BLN BRO GRY RED SDY WHI UNK"},
    "DAW": {"label": "Physical Description — Weight (lbs)",   "type": "N",  "min": 3,  "max": 3,  "presence": "O", "version_added": 1, "subfile": "DL/ID", "desc": "Weight in pounds, 000-999"},
    "DAX": {"label": "Physical Description — Weight Range",   "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 5, "subfile": "DL/ID", "desc": "0=up to 70, 1=71-100, 2=101-130, ..., 9=Over 300 lbs"},
    "DAV": {"label": "Physical Description — Weight (kg)",    "type": "N",  "min": 3,  "max": 3,  "presence": "O", "version_added": 3, "subfile": "DL/ID", "desc": "Weight in kilograms"},
    "DCE": {"label": "Physical Description — Weight Range",   "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Weight range code"},
    "DCI": {"label": "Place of Birth",                        "type": "AN", "min": 2,  "max": 33, "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "State/country of birth"},
    "DCJ": {"label": "Audit Information",                     "type": "AN", "min": 4,  "max": 25, "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Audit trail ID from issuing jurisdiction"},
    "DCK": {"label": "Inventory Control Number",              "type": "AN", "min": 4,  "max": 25, "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Inventory/batch control number"},
    "DBN": {"label": "Alias / AKA Family Name",               "type": "AN", "min": 0,  "max": 10, "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Alias last name"},
    "DBG": {"label": "Alias / AKA Given Name",                "type": "AN", "min": 0,  "max": 15, "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Alias first name"},
    "DBS": {"label": "Alias / AKA Suffix Name",               "type": "AN", "min": 0,  "max": 5,  "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "Alias suffix"},
    "DCU": {"label": "Name Suffix",                           "type": "AN", "min": 0,  "max": 5,  "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "JR, SR, I, II, III, IV, V, VI, VII, VIII, IX, X"},
    "DCL": {"label": "Race / Ethnicity",                      "type": "A",  "min": 3,  "max": 3,  "presence": "O", "version_added": 4, "subfile": "DL/ID", "desc": "AI=Am. Indian, AP=Asian/Pacific, BK=Black, HI=Hispanic, O=Other, W=White"},
    "DCM": {"label": "Standard Vehicle Classification",       "type": "AN", "min": 4,  "max": 4,  "presence": "O", "version_added": 4, "subfile": "DL",    "desc": "AAMVA standard vehicle class code"},
    "DCN": {"label": "Standard Endorsement Code",             "type": "AN", "min": 0,  "max": 5,  "presence": "O", "version_added": 4, "subfile": "DL",    "desc": "AAMVA standard endorsement code"},
    "DCO": {"label": "Standard Restriction Code",             "type": "AN", "min": 0,  "max": 12, "presence": "O", "version_added": 4, "subfile": "DL",    "desc": "AAMVA standard restriction code"},
    "DCP": {"label": "Jurisdiction-Specific Vehicle Class Description", "type": "AN", "min": 4, "max": 50, "presence": "O", "version_added": 4, "subfile": "DL", "desc": "Text description of vehicle class"},
    "DCQ": {"label": "Jurisdiction-Specific Endorsement Code Description", "type": "AN", "min": 4, "max": 50, "presence": "O", "version_added": 4, "subfile": "DL", "desc": "Text description of endorsement"},
    "DCR": {"label": "Jurisdiction-Specific Restriction Code Description", "type": "AN", "min": 4, "max": 50, "presence": "O", "version_added": 4, "subfile": "DL", "desc": "Text description of restriction"},
    "DDA": {"label": "Compliance Type",                       "type": "A",  "min": 1,  "max": 1,  "presence": "O", "version_added": 5, "subfile": "DL/ID", "desc": "F=Full compliance, N=Non-compliant"},
    "DDB": {"label": "Card Revision Date",                    "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 5, "subfile": "DL/ID", "desc": "Date card design was revised"},
    "DDC": {"label": "HAZMAT Endorsement Expiration Date",    "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 5, "subfile": "DL",    "desc": "HAZMAT endorsement expiry date"},
    "DDD": {"label": "Limited Duration Document Indicator",   "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 5, "subfile": "DL/ID", "desc": "1=Limited duration document"},
    "DAR": {"label": "License Classification Code",           "type": "A",  "min": 2,  "max": 5,  "presence": "O", "version_added": 1, "subfile": "DL",    "desc": "License classification"},
    "DAS": {"label": "License Restriction Code",              "type": "A",  "min": 2,  "max": 12, "presence": "O", "version_added": 1, "subfile": "DL",    "desc": "License restriction code(s)"},
    "DAT": {"label": "License Endorsements Code",             "type": "A",  "min": 2,  "max": 5,  "presence": "O", "version_added": 1, "subfile": "DL",    "desc": "Endorsement code(s)"},
    "DCH": {"label": "Federal Commercial Vehicle Codes",      "type": "AN", "min": 4,  "max": 5,  "presence": "O", "version_added": 2, "subfile": "DL",    "desc": "Federal commercial vehicle class"},
    "DBH": {"label": "Under 18 Until",                        "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 2, "subfile": "DL/ID", "desc": "Date person turns 18"},
    "DBI": {"label": "Under 19 Until",                        "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 2, "subfile": "DL/ID", "desc": "Date person turns 19"},
    "DBJ": {"label": "Under 21 Until",                        "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 2, "subfile": "DL/ID", "desc": "Date person turns 21"},
    "DBK": {"label": "Organ Donor Indicator",                 "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 2, "subfile": "DL/ID", "desc": "1=Organ donor"},
    "DBL": {"label": "Veteran Indicator",                     "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 9, "subfile": "DL/ID", "desc": "1=Veteran"},
    "DBM": {"label": "Organ Donor (older format)",            "type": "N",  "min": 1,  "max": 1,  "presence": "O", "version_added": 1, "subfile": "DL/ID", "desc": "Older organ donor field"},
    "DBR": {"label": "Suffix",                                "type": "AN", "min": 0,  "max": 5,  "presence": "O", "version_added": 1, "subfile": "DL/ID", "desc": "Name suffix"},
    "PAA": {"label": "Permit Classification Code",            "type": "AN", "min": 4,  "max": 6,  "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit class"},
    "PAB": {"label": "Permit Expiration Date",                "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit expiry"},
    "PAC": {"label": "Permit Identifier",                     "type": "AN", "min": 1,  "max": 25, "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit number"},
    "PAD": {"label": "Permit Issue Date",                     "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit issue date"},
    "PAE": {"label": "Permit Restriction Code",               "type": "AN", "min": 0,  "max": 12, "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit restrictions"},
    "PAF": {"label": "Permit Endorsement Code",               "type": "AN", "min": 0,  "max": 5,  "presence": "O", "version_added": 3, "subfile": "DL",    "desc": "Learner's permit endorsements"},
    "ZVA": {"label": "Court Restriction Code",                "type": "AN", "min": 4,  "max": 25, "presence": "O", "version_added": 4, "subfile": "ZV",    "desc": "Court-ordered restriction"},
    "ZVB": {"label": "Court Restriction Expiry Date",         "type": "D",  "min": 8,  "max": 8,  "presence": "O", "version_added": 4, "subfile": "ZV",    "desc": "Date court restriction expires"},
}

# ── Annex E: Standard Vehicle Class Codes ────────────────────────────────────
STD_VEHICLE_CLASSES = {
    "A":  "Combination vehicle >= 26,001 lbs GVWR",
    "B":  "Single vehicle >= 26,001 lbs GVWR",
    "C":  "Single vehicle < 26,001 lbs GVWR",
    "D":  "Non-commercial operator",
    "M":  "Motorcycle",
    "L":  "Moped",
    "R":  "Recreational vehicle",
    "F":  "Fire/emergency (state-specific)",
    "P":  "Passengers (commercial)",
    "S":  "School bus",
    "T":  "Double/triple trailers",
    "X":  "Combined tank / HAZMAT",
}

# ── Annex E: Standard Endorsement Codes ──────────────────────────────────────
STD_ENDORSEMENTS = {
    "H":  "HAZMAT",
    "L":  "Motorcycles",
    "N":  "Tank vehicles",
    "P":  "Passengers",
    "S":  "School bus",
    "T":  "Double/triple trailers",
    "X":  "Combined Tank / HAZMAT",
    "NONE": "No endorsement",
}

# ── Annex E: Standard Restriction Codes ──────────────────────────────────────
STD_RESTRICTIONS = {
    "B":  "Corrective lenses",
    "C":  "Mechanical devices (special brakes, hand controls, or other)",
    "D":  "Prosthetic device",
    "E":  "Automatic transmission",
    "F":  "Outside mirror",
    "G":  "Limit to daylight driving",
    "H":  "Limit to employment",
    "I":  "Limited — other",
    "J":  "Other",
    "K":  "CDL intrastate only",
    "L":  "No air-brake equipped CMV",
    "M":  "No Class A passenger vehicle",
    "N":  "No Class A and B passenger vehicle",
    "O":  "No tractor-trailer CMV",
    "V":  "Medical variance documentation required",
    "W":  "Farm waiver",
    "NONE": "No restriction",
}

# ── Annex E: Hair Color Codes ─────────────────────────────────────────────────
HAIR_COLORS = {"BAL", "BLK", "BLN", "BRO", "GRY", "RED", "SDY", "WHI", "UNK"}

# ── Annex B: Eye Color Codes ──────────────────────────────────────────────────
EYE_COLORS = {"BLK", "BLU", "BRN", "GRY", "GRN", "HAZ", "MAR", "PNK", "DIC", "UNK"}

# ── Annex B: Sex Codes ────────────────────────────────────────────────────────
SEX_CODES = {"1": "Male", "2": "Female", "9": "Not Specified / Unknown"}

# ── Annex B: Truncation Codes ─────────────────────────────────────────────────
TRUNC_CODES = {"T": "Truncated", "N": "Not truncated", "U": "Unknown"}

# ── Annex B: Compliance Type Codes ───────────────────────────────────────────
COMPLIANCE_TYPES = {"F": "Fully REAL ID compliant", "N": "Non-compliant"}

# ── Annex B: Weight Range Codes ──────────────────────────────────────────────
WEIGHT_RANGES = {
    "0": "Up to 70 lbs (31 kg)",
    "1": "71-100 lbs (32-45 kg)",
    "2": "101-130 lbs (46-59 kg)",
    "3": "131-160 lbs (60-70 kg)",
    "4": "161-190 lbs (71-86 kg)",
    "5": "191-220 lbs (87-100 kg)",
    "6": "221-250 lbs (101-113 kg)",
    "7": "251-280 lbs (114-127 kg)",
    "8": "281-320 lbs (128-145 kg)",
    "9": "Over 320 lbs (over 145 kg)",
}

# ── Annex F: Jurisdiction-specific elements by state ─────────────────────────
# Each entry: element_id -> label (jurisdiction prefix is part of element ID)
JURISDICTION_ELEMENTS = {
    # California (ZC prefix)
    "ZCA": "CA - Driver License / ID Number",
    "ZCB": "CA - Hair Color",
    "ZCC": "CA - Eyes Color",
    "ZCD": "CA - Misc",
    # Texas (ZT prefix)
    "ZTA": "TX - County",
    "ZTB": "TX - Suffix",
    "ZTC": "TX - CVC Misc",
    # New York
    "ZNA": "NY - County",
    "ZNB": "NY - Suffix",
    # Florida
    "ZFA": "FL - Vision Aid",
    "ZFB": "FL - Type",
    # Illinois
    "ZIA": "IL - County",
    "ZIB": "IL - Suffix",
    # Generic ZX (most states)
    "ZXA": "Jurisdiction Extension A",
    "ZXB": "Jurisdiction Extension B",
    "ZXC": "Jurisdiction Extension C",
    "ZXD": "Jurisdiction Extension D",
    "ZXE": "Jurisdiction Extension E",
    "ZXF": "Jurisdiction Extension F",
    "ZXG": "Jurisdiction Extension G",
    "ZXH": "Jurisdiction Extension H",
    "ZXI": "Jurisdiction Extension I",
    "ZXJ": "Jurisdiction Extension J",
    "ZXK": "Jurisdiction Extension K",
}

# ── Annex D: Subfile Type Registry ───────────────────────────────────────────
SUBFILE_TYPES = {
    "DL": "Driver License",
    "ID": "Identification Card",
    "ZV": "Vital Statistics Subfile",
    "ZN": "Name Alias Subfile",
    "ZW": "Temporary Visitor Subfile",
    "ZX": "Jurisdiction-Specific Subfile",
    "ZZ": "Future Use / Undefined Subfile",
    "ZC": "California Jurisdiction Subfile",
    "ZT": "Texas Jurisdiction Subfile",
    "ZF": "Florida Jurisdiction Subfile",
    "ZI": "Illinois Jurisdiction Subfile",
    "ZA": "Alaska Jurisdiction Subfile",
    "ZM": "Michigan Jurisdiction Subfile",
    "ZO": "Ohio Jurisdiction Subfile",
    "ZP": "Pennsylvania Jurisdiction Subfile",
    "ZG": "Georgia Jurisdiction Subfile",
    "ZNA": "New York Jurisdiction Subfile",
    "ZNC": "North Carolina Jurisdiction Subfile",
    "ZNE": "Nebraska Jurisdiction Subfile",
    "ZNH": "New Hampshire Jurisdiction Subfile",
    "ZNJ": "New Jersey Jurisdiction Subfile",
    "ZNM": "New Mexico Jurisdiction Subfile",
    "ZNV": "Nevada Jurisdiction Subfile",
    "ZNY": "New York (alt) Jurisdiction Subfile",
}

# ── Mandatory fields by version ───────────────────────────────────────────────
# Returns set of element IDs that MUST be present for a given AAMVA version
def mandatory_for_version(version: int, subfile_type: str) -> dict:
    result = {}
    for eid, meta in ELEMENT_CATALOG.items():
        if meta["presence"] == "M" and meta["version_added"] <= version:
            sf = meta["subfile"]
            if subfile_type in sf or sf == "DL/ID":
                result[eid] = meta["label"]
    return result


def element_label(eid: str) -> str:
    if eid in ELEMENT_CATALOG:
        return ELEMENT_CATALOG[eid]["label"]
    if eid in JURISDICTION_ELEMENTS:
        return JURISDICTION_ELEMENTS[eid]
    return "Unknown / Jurisdiction-specific element"
