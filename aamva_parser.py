"""
AAMVA DL/ID PDF417 Barcode Parser & Validator
Implements AAMVA DL/ID Card Design Standard versions 1-10 (2000-2025).
Reference: AAMVA 2020/2025 DL/ID Card Design Standard, Annex D.
Anti-fake checks: IIN registry, cross-date logic, field format, state/IIN mismatch.
"""
import re
from datetime import date

# ── Complete Issuer Identification Number (IIN) registry
# Source: AAMVA 2020 Standard Table D-1 — all 50 states + DC + territories + CA provinces
AAMVA_IIN = {
    "636000":("Virginia","VA","US"),      "636001":("New York","NY","US"),
    "636002":("Massachusetts","MA","US"), "636003":("Maryland","MD","US"),
    "636004":("North Carolina","NC","US"),"636005":("South Carolina","SC","US"),
    "636006":("Connecticut","CT","US"),   "636007":("Louisiana","LA","US"),
    "636008":("Arkansas","AR","US"),      "636009":("Texas","TX","US"),
    "636010":("Colorado","CO","US"),      "636011":("Georgia","GA","US"),
    "636012":("Arizona","AZ","US"),       "636013":("California","CA","US"),
    "636014":("Hawaii","HI","US"),        "636015":("Kansas","KS","US"),
    "636016":("Mississippi","MS","US"),   "636017":("New Hampshire","NH","US"),
    "636018":("New Jersey","NJ","US"),    "636019":("Michigan","MI","US"),
    "636020":("Illinois","IL","US"),      "636021":("Pennsylvania","PA","US"),
    "636022":("Kentucky","KY","US"),      "636023":("Ohio","OH","US"),
    "636024":("Florida","FL","US"),       "636025":("Tennessee","TN","US"),
    "636026":("Indiana","IN","US"),       "636027":("Alabama","AL","US"),
    "636028":("Nebraska","NE","US"),      "636029":("Missouri","MO","US"),
    "636030":("Iowa","IA","US"),          "636031":("Minnesota","MN","US"),
    "636032":("Wisconsin","WI","US"),     "636033":("Washington","WA","US"),
    "636034":("Oregon","OR","US"),        "636035":("Nevada","NV","US"),
    "636036":("Idaho","ID","US"),         "636037":("Montana","MT","US"),
    "636038":("Wyoming","WY","US"),       "636039":("North Dakota","ND","US"),
    "636040":("South Dakota","SD","US"),  "636041":("Utah","UT","US"),
    "636042":("New Mexico","NM","US"),    "636043":("Oklahoma","OK","US"),
    "636044":("Maine","ME","US"),         "636045":("Delaware","DE","US"),
    "636046":("Rhode Island","RI","US"),  "636047":("Vermont","VT","US"),
    "636048":("Alaska","AK","US"),        "636049":("West Virginia","WV","US"),
    "636050":("District of Columbia","DC","US"),
    "636051":("Puerto Rico","PR","US"),   "636052":("US Virgin Islands","VI","US"),
    "636053":("Guam","GU","US"),          "636220":("American Samoa","AS","US"),
    "636055":("Ontario","ON","CA"),       "636056":("Quebec","QC","CA"),
    "636057":("British Columbia","BC","CA"),"636058":("Alberta","AB","CA"),
    "636059":("Manitoba","MB","CA"),      "636060":("Saskatchewan","SK","CA"),
    "636061":("Nova Scotia","NS","CA"),   "636062":("New Brunswick","NB","CA"),
    "636063":("Newfoundland","NL","CA"),  "636064":("Prince Edward Island","PE","CA"),
    "636065":("Northwest Territories","NT","CA"),"636066":("Yukon","YT","CA"),
    "604427":("Alberta","AB","CA"),
}

MANDATORY_ELEMENTS = {
    "DCA":"Vehicle Class","DCB":"Restriction Codes","DCD":"Endorsement Codes",
    "DBA":"Expiry Date","DCS":"Last Name","DAC":"First Name","DAD":"Middle Name",
    "DBD":"Issue Date","DBB":"Date of Birth","DBC":"Sex","DAY":"Eye Color",
    "DAU":"Height","DAG":"Street Address","DAI":"City","DAJ":"State/Province",
    "DAK":"Postal Code","DAQ":"License/ID Number","DCF":"Document Discriminator",
    "DCG":"Country Identification","DDE":"Family Name Truncation",
    "DDF":"First Name Truncation","DDG":"Middle Name Truncation",
}

EYE_COLORS  = {"BLK","BLU","BRN","GRY","GRN","HAZ","MAR","PNK","DIC","UNK"}
SEX_CODES   = {"1":"Male","2":"Female","9":"Unknown/Not Specified"}
TRUNC_CODES = {"T","N","U"}

AAMVA_HEADER_RE = re.compile(
    r"@\n?\x1c?\r?ANSI\s+(\d{6})(\d{2})(\d{2})(\d{2})", re.DOTALL
)


def parse_header(raw: str):
    m = AAMVA_HEADER_RE.search(raw)
    if not m:
        return None
    return {
        "iin": m.group(1),
        "aamva_version": int(m.group(2)),
        "jurisdiction_version": int(m.group(3)),
        "num_entries": int(m.group(4)),
        "match_end": m.end(),
    }


def parse_elements(text: str):
    elements = {}
    for line in re.split(r"[\r\n]+", text):
        line = line.strip()
        if len(line) >= 4 and re.match(r"^[A-Z]{3}", line[:3]):
            key, val = line[:3], line[3:].strip()
            if val:
                elements[key] = val
    return elements


def parse_date(val: str, version: int):
    val = val.strip()
    if len(val) != 8 or not val.isdigit():
        return None, f"Invalid date string '{val}' (must be 8 digits)"
    try:
        if version <= 8:   # MMDDCCYY (AAMVA v1-v8)
            mm, dd, ccyy = val[0:2], val[2:4], val[4:8]
        else:              # CCYYMMDD (AAMVA v9+)
            ccyy, mm, dd = val[0:4], val[4:6], val[6:8]
        return date(int(ccyy), int(mm), int(dd)), None
    except ValueError as e:
        return None, str(e)


def validate_elements(elements, version, iin):
    issues, warnings, parsed = [], [], {}

    # Date of Birth
    if "DBB" in elements:
        dob, err = parse_date(elements["DBB"], version)
        if err:
            issues.append(f"DBB (Date of Birth): {err}")
        else:
            parsed["date_of_birth"] = dob.isoformat()
            age = (date.today() - dob).days // 365
            if age < 14 or age > 120:
                warnings.append(f"DBB: Suspicious age — {age} years")

    # Expiry Date
    if "DBA" in elements:
        exp, err = parse_date(elements["DBA"], version)
        if err:
            issues.append(f"DBA (Expiry Date): {err}")
        else:
            parsed["expiry_date"] = exp.isoformat()
            if exp < date.today():
                warnings.append("DBA: Document is EXPIRED")

    # Issue Date
    if "DBD" in elements:
        iss, err = parse_date(elements["DBD"], version)
        if err:
            issues.append(f"DBD (Issue Date): {err}")
        else:
            parsed["issue_date"] = iss.isoformat()
            if iss > date.today():
                issues.append("DBD: Issue date is in the future — impossible on a real document")

    # Cross-date sanity (anti-fake)
    if "issue_date" in parsed and "expiry_date" in parsed:
        i = date.fromisoformat(parsed["issue_date"])
        e = date.fromisoformat(parsed["expiry_date"])
        if e <= i:
            issues.append("Expiry date is not after issue date — impossible")

    if "date_of_birth" in parsed and "issue_date" in parsed:
        d = date.fromisoformat(parsed["date_of_birth"])
        i = date.fromisoformat(parsed["issue_date"])
        if i < d:
            issues.append("Issue date is before date of birth — impossible")

    if "date_of_birth" in parsed and "expiry_date" in parsed:
        d = date.fromisoformat(parsed["date_of_birth"])
        e = date.fromisoformat(parsed["expiry_date"])
        if (e - d).days // 365 > 125:
            issues.append("Expiry date is >125 years after DOB — impossible")

    # Sex code
    if "DBC" in elements:
        sex = elements["DBC"].strip()
        if sex not in SEX_CODES:
            issues.append(f"DBC (Sex): Invalid code '{sex}' — must be 1 (Male), 2 (Female), or 9")
        else:
            parsed["sex"] = SEX_CODES[sex]

    # Eye color
    if "DAY" in elements:
        eye = elements["DAY"].strip().upper()
        if eye not in EYE_COLORS:
            issues.append(f"DAY (Eye Color): Invalid code '{eye}' — must be one of {sorted(EYE_COLORS)}")
        else:
            parsed["eye_color"] = eye

    # Height
    if "DAU" in elements:
        h = elements["DAU"].strip()
        if not re.match(r"^\d{3}(IN|CM)$", h, re.IGNORECASE):
            issues.append(f"DAU (Height): Invalid format '{h}' — must be nnnIN or nnnCM")
        else:
            parsed["height"] = h

    # Truncation codes
    for code, label in [("DDE","Family Name"),("DDF","First Name"),("DDG","Middle Name")]:
        if code in elements:
            v = elements[code].strip().upper()
            if v not in TRUNC_CODES:
                issues.append(f"{code} ({label} Truncation): Invalid code '{v}' — must be T, N, or U")

    # Country
    if "DCG" in elements:
        c = elements["DCG"].strip().upper()
        if c not in ("USA", "CAN", "MEX"):
            warnings.append(f"DCG (Country): Unusual value '{c}'")
        else:
            parsed["country"] = c

    # Mandatory fields (AAMVA v2+)
    if version >= 2:
        for mk, ml in MANDATORY_ELEMENTS.items():
            if mk not in elements:
                warnings.append(f"Missing mandatory field {mk} ({ml})")

    # IIN vs DAJ state cross-check — primary fake-detector
    if "DAJ" in elements and iin in AAMVA_IIN:
        expected = AAMVA_IIN[iin][1]
        barcode_state = elements["DAJ"].strip().upper()
        if barcode_state != expected:
            issues.append(
                f"CRITICAL STATE MISMATCH: IIN {iin} is registered to "
                f"{AAMVA_IIN[iin][0]} ({expected}), "
                f"but barcode field DAJ says '{barcode_state}'. "
                f"Strong indicator of a fabricated barcode."
            )

    # Postal code format
    if "DAK" in elements:
        pk = re.sub(r"[\s\-]", "", elements["DAK"])
        if not (re.match(r"^\d{5,9}$", pk) or re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", pk, re.I)):
            issues.append(f"DAK (Postal Code): Suspicious format '{elements['DAK']}'")

    return issues, warnings, parsed


def validate_aamva_raw(raw: str):
    """Master entry point. Returns a structured validation result dict."""
    result = {
        "valid": False,
        "score": 0,
        "issues": [],
        "warnings": [],
        "fields": {},
        "header": {},
        "subfile_type": None,
    }

    if not raw:
        result["issues"].append("Empty barcode data")
        return result

    header = parse_header(raw)
    if not header:
        result["issues"].append(
            "AAMVA header signature not found. "
            "Real AAMVA barcodes begin with @\\n\\x1c\\rANSI followed by the 6-digit IIN. "
            "This barcode does not conform to AAMVA Annex D structure."
        )
        return result

    result["header"] = header
    iin, version = header["iin"], header["aamva_version"]

    if iin in AAMVA_IIN:
        j = AAMVA_IIN[iin]
        result["fields"]["issuer"] = {
            "iin": iin, "state": j[0], "abbreviation": j[1], "country": j[2]
        }
    else:
        result["issues"].append(
            f"IIN '{iin}' is NOT in the AAMVA jurisdiction registry. "
            f"All legitimate US/Canadian licenses use registered IINs. "
            f"Primary indicator of a fabricated barcode."
        )

    if not (1 <= version <= 10):
        result["issues"].append(f"AAMVA version {version} is outside valid range (1-10)")
    else:
        result["fields"]["aamva_version"] = version

    # Locate DL or ID subfile
    subfile_body = None
    for st in ("DL", "ID"):
        idx = raw.find(st, header["match_end"])
        if idx != -1:
            result["subfile_type"] = st
            subfile_body = raw[idx:]
            break

    if not subfile_body:
        result["issues"].append("No DL or ID subfile found in barcode body")
        return result

    elements = parse_elements(subfile_body)
    result["fields"]["elements"] = elements

    vi, vw, vp = validate_elements(elements, version, iin)
    result["issues"]   += vi
    result["warnings"] += vw
    result["fields"].update(vp)

    score = 100 - len(result["issues"]) * 15 - len(result["warnings"]) * 3
    result["score"] = max(0, min(100, score))
    result["valid"] = len(result["issues"]) == 0
    return result
