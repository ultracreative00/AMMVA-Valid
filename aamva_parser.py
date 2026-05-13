"""
AAMVA DL/ID PDF417 Barcode Parser & Validator
Implements AAMVA DL/ID Card Design Standard versions 1-10 (2000-2025).

Header format (Annex D):
  Byte sequence: 0x40 0x0A 0x1C 0x0D  followed by  'ANSI ' + IIN(6) + versions
  '@'  LF   FS   CR   A  N  S  I  space  [6-digit IIN][AA][JJ][EE]
  0x40 0x0A 0x1C 0x0D 0x41 0x4E 0x53 0x49 0x20 ...

Anti-fake detection layers (preserved, false-positive causes fixed):
  1.  Flexible header regex covering all real scanner byte sequences
  2.  IIN registry - all 50 states, DC, territories, CA provinces
  3.  IIN <-> DAJ state cross-match (hard ISSUE)
  4.  Cross-date logical impossibility (hard ISSUE)
  5.  Field format per Annex B (hard ISSUE)
  6.  Mandatory field presence (WARNING - states legitimately omit optional fields)
  7.  Subfile directory structure
  8.  Element length bounds
  9.  Endorsement/restriction codes (WARNING - state codes vary)
  10. Compliance type indicator
"""

import re
from datetime import date

try:
    from aamva_data_elements import (
        ELEMENT_CATALOG, SUBFILE_TYPES, JURISDICTION_ELEMENTS,
        EYE_COLORS, HAIR_COLORS, SEX_CODES, TRUNC_CODES, COMPLIANCE_TYPES,
        WEIGHT_RANGES, STD_VEHICLE_CLASSES, STD_ENDORSEMENTS, STD_RESTRICTIONS,
        mandatory_for_version, element_label,
    )
except ImportError:
    ELEMENT_CATALOG = {}
    SUBFILE_TYPES = {
        "DL": "Driver License",
        "ID": "Identification Card",
        "ZA": "Arizona Jurisdiction",  "ZC": "California Jurisdiction",
        "ZF": "Florida Jurisdiction",  "ZG": "Georgia Jurisdiction",
        "ZI": "Illinois Jurisdiction", "ZM": "Michigan Jurisdiction",
        "ZN": "Minnesota Jurisdiction","ZO": "Ohio Jurisdiction",
        "ZT": "Texas Jurisdiction",    "ZV": "Virginia Jurisdiction",
        "ZW": "Washington Jurisdiction",
    }
    JURISDICTION_ELEMENTS = {}
    EYE_COLORS   = {"BLK","BLU","BRN","GRY","GRN","HAZ","MAR","PNK","DIC","UNK"}
    HAIR_COLORS  = {"BAL","BLK","BLN","BRO","GRY","RED","SDY","WHI","UNK"}
    SEX_CODES    = {"1": "Male", "2": "Female", "9": "Unknown"}
    TRUNC_CODES  = {"T": "Truncated", "N": "Not Truncated", "U": "Unknown"}
    COMPLIANCE_TYPES = {"F": "Fully Compliant", "N": "Non-Compliant"}
    WEIGHT_RANGES = {str(i): f"Range {i}" for i in range(10)}
    STD_VEHICLE_CLASSES = set("ABCDM")
    STD_ENDORSEMENTS = {"H","L","N","P","S","T","X","NONE"}
    STD_RESTRICTIONS = {"B","C","D","E","F","G","I","J","K","L","M",
                        "N","O","V","W","NONE"}
    def mandatory_for_version(v, st): return {}
    def element_label(eid): return eid


# -- Complete IIN registry (AAMVA Annex D, Table D-1) --------------------------
AAMVA_IIN = {
    "636000":("Virginia",             "VA","US"), "636001":("New York",           "NY","US"),
    "636002":("Massachusetts",        "MA","US"), "636003":("Maryland",           "MD","US"),
    "636004":("North Carolina",       "NC","US"), "636005":("South Carolina",     "SC","US"),
    "636006":("Connecticut",          "CT","US"), "636007":("Louisiana",          "LA","US"),
    "636008":("Arkansas",             "AR","US"), "636009":("Texas",              "TX","US"),
    "636010":("Colorado",             "CO","US"), "636011":("Georgia",            "GA","US"),
    "636012":("Arizona",              "AZ","US"), "636013":("California",         "CA","US"),
    "636014":("Hawaii",               "HI","US"), "636015":("Kansas",             "KS","US"),
    "636016":("Mississippi",          "MS","US"), "636017":("New Hampshire",      "NH","US"),
    "636018":("New Jersey",           "NJ","US"), "636019":("Michigan",           "MI","US"),
    "636020":("Illinois",             "IL","US"), "636021":("Pennsylvania",       "PA","US"),
    "636022":("Kentucky",             "KY","US"), "636023":("Ohio",               "OH","US"),
    "636024":("Florida",              "FL","US"), "636025":("Tennessee",          "TN","US"),
    "636026":("Indiana",              "IN","US"), "636027":("Alabama",            "AL","US"),
    "636028":("Nebraska",             "NE","US"), "636029":("Missouri",           "MO","US"),
    "636030":("Iowa",                 "IA","US"), "636031":("Minnesota",          "MN","US"),
    "636032":("Wisconsin",            "WI","US"), "636033":("Washington",         "WA","US"),
    "636034":("Oregon",               "OR","US"), "636035":("Nevada",             "NV","US"),
    "636036":("Idaho",                "ID","US"), "636037":("Montana",            "MT","US"),
    "636038":("Wyoming",              "WY","US"), "636039":("North Dakota",       "ND","US"),
    "636040":("South Dakota",         "SD","US"), "636041":("Utah",               "UT","US"),
    "636042":("New Mexico",           "NM","US"), "636043":("Oklahoma",           "OK","US"),
    "636044":("Maine",                "ME","US"), "636045":("Delaware",           "DE","US"),
    "636046":("Rhode Island",         "RI","US"), "636047":("Vermont",            "VT","US"),
    "636048":("Alaska",               "AK","US"), "636049":("West Virginia",      "WV","US"),
    "636050":("District of Columbia", "DC","US"), "636051":("Puerto Rico",        "PR","US"),
    "636052":("US Virgin Islands",    "VI","US"), "636053":("Guam",               "GU","US"),
    "636220":("American Samoa",       "AS","US"),
    "636055":("Ontario",              "ON","CA"), "636056":("Quebec",             "QC","CA"),
    "636057":("British Columbia",     "BC","CA"), "636058":("Alberta",            "AB","CA"),
    "636059":("Manitoba",             "MB","CA"), "636060":("Saskatchewan",       "SK","CA"),
    "636061":("Nova Scotia",          "NS","CA"), "636062":("New Brunswick",      "NB","CA"),
    "636063":("Newfoundland",         "NL","CA"), "636064":("Prince Edward Island","PE","CA"),
    "636065":("Northwest Territories","NT","CA"), "636066":("Yukon",              "YT","CA"),
    "604427":("Alberta (alt IIN)",    "AB","CA"),
}


# -- Header regex (Annex D) ----------------------------------------------------
# The spec mandates: 0x40 0x0A 0x1C 0x0D then 'ANSI ' + IIN
# Real scanners and libraries produce various subsets of these control bytes.
# Strategy: anchor on '@' (if present) OR 'ANSI' directly, capture IIN after.
#
# Pattern A: @ followed by any mix of control chars then ANSI
# Pattern B: ANSI with no @ prefix (some decoders strip leading bytes)
_HEADER_PAT_A = re.compile(
    r"@[\x00-\x1f\s]*ANSI[\x00-\x1f\s]*(\d{6})(\d{2})(\d{2})(\d{2})",
    re.DOTALL
)
_HEADER_PAT_B = re.compile(
    r"ANSI[\x00-\x1f\s]*(\d{6})(\d{2})(\d{2})(\d{2})",
    re.DOTALL
)


def parse_header(raw: str):
    """Parse AAMVA file header. Returns dict or None."""
    # Try strict pattern first (requires @)
    m = _HEADER_PAT_A.search(raw)
    if not m:
        # Fallback: accept ANSI without @ (decoder stripped leading byte)
        m = _HEADER_PAT_B.search(raw)
    if not m:
        return None
    return {
        "iin":                  m.group(1),
        "aamva_version":        int(m.group(2)),
        "jurisdiction_version": int(m.group(3)),
        "num_entries":          int(m.group(4)),
        "header_end":           m.end(),
    }


# -- Subfile directory parser (Annex D) ----------------------------------------
_SUBFILE_DIR_RE = re.compile(r"([A-Z]{2})(\d{4})(\d{4})")


def parse_subfile_directory(raw: str, header_end: int, num_entries: int):
    text = raw[header_end: header_end + (num_entries * 10) + 30]
    entries = []
    for m in _SUBFILE_DIR_RE.finditer(text):
        entries.append({
            "type":   m.group(1),
            "offset": int(m.group(2)),
            "length": int(m.group(3)),
        })
        if len(entries) >= num_entries:
            break
    return entries


# -- Helpers -------------------------------------------------------------------
def _clean(val: str) -> str:
    """Strip null bytes, padding, and surrounding whitespace from a field value."""
    return val.strip().rstrip("\x00").strip()


def parse_date(val: str, version: int):
    """Parse AAMVA date. Returns (date, None) or (None, error_string)."""
    val = _clean(val)
    digits = re.sub(r"\D", "", val)  # extract digits only (handles padding)
    if len(digits) != 8:
        return None, f"Need 8 digits, got {len(digits)} in '{val}'"
    try:
        if version <= 8:   # MMDDCCYY
            mm, dd, yyyy = digits[0:2], digits[2:4], digits[4:8]
        else:              # CCYYMMDD
            yyyy, mm, dd = digits[0:4], digits[4:6], digits[6:8]
        return date(int(yyyy), int(mm), int(dd)), None
    except ValueError as e:
        return None, str(e)


# -- Element parser ------------------------------------------------------------
def parse_elements(text: str) -> dict:
    """
    Extract data elements from a subfile body.
    Handles LF, CR, CR+LF line endings.
    Element format: <3-char-ID><value>  (no separator between ID and value).
    """
    # Normalise all line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    elements = {}
    for line in text.split("\n"):
        # Must start with exactly 3 uppercase letters = element ID
        if len(line) >= 4 and re.match(r"^[A-Z]{3}", line[:3]):
            eid = line[:3]
            val = line[3:].rstrip("\x00").rstrip()  # preserve leading spaces in value
            if val and eid not in elements:
                elements[eid] = val
    return elements


# -- Element value validator ---------------------------------------------------
def _validate_element(eid: str, val: str) -> list:
    """Check a single element against the Annex B catalog. Returns list of issues."""
    meta = ELEMENT_CATALOG.get(eid)
    if not meta:
        return []  # Jurisdiction-specific or unknown - never flag
    issues = []
    max_len = meta.get("max", 0)
    if max_len > 0 and len(val) > max_len:
        issues.append(
            f"{eid} ({meta.get('label', eid)}): length {len(val)} exceeds max {max_len}"
        )
    if meta.get("type") == "N":
        if not re.match(r"^\d+$", re.sub(r"[\s\x00]", "", val)):
            issues.append(f"{eid} ({meta.get('label', eid)}): must be numeric")
    return issues


# -- Full element set validator ------------------------------------------------
def validate_elements(elements: dict, version: int, iin: str, subfile_type: str):
    issues, warnings, parsed = [], [], {}

    # Date fields
    DATE_FIELDS = {
        "DBB":("Date of Birth",    "date_of_birth"),
        "DBA":("Expiry Date",      "expiry_date"),
        "DBD":("Issue Date",       "issue_date"),
        "DDB":("Card Revision",    "card_revision_date"),
        "DDC":("HAZMAT Expiry",    "hazmat_expiry"),
        "DBH":("Under 18 Until",   "under_18_until"),
        "DBI":("Under 19 Until",   "under_19_until"),
        "DBJ":("Under 21 Until",   "under_21_until"),
    }
    for eid, (label, key) in DATE_FIELDS.items():
        if eid in elements:
            d, err = parse_date(elements[eid], version)
            if err:
                issues.append(f"{eid} ({label}): {err}")
            else:
                parsed[key] = d.isoformat()

    # Cross-date logic (hard issues = true impossibilities only)
    dob = date.fromisoformat(parsed["date_of_birth"]) if "date_of_birth" in parsed else None
    iss = date.fromisoformat(parsed["issue_date"])     if "issue_date"     in parsed else None
    exp = date.fromisoformat(parsed["expiry_date"])    if "expiry_date"    in parsed else None
    today = date.today()

    if dob:
        age = (today - dob).days // 365
        if age < 13 or age > 120:
            warnings.append(f"DBB: Calculated age is {age} years")
        if iss and iss < dob:
            issues.append("DBD: Issue date is before date of birth - impossible")
        if exp and (exp - dob).days // 365 > 125:
            issues.append("DBA: Expiry > 125 years after DOB - impossible")

    if iss and iss > today:
        issues.append("DBD: Issue date is in the future - impossible on a genuine document")

    if exp and exp < today:
        warnings.append("DBA: Document is EXPIRED")

    if exp and iss and exp <= iss:
        issues.append("DBA: Expiry date is on or before issue date - impossible")

    # Under-age markers (warnings only)
    for u_key, u_eid, u_yrs in [
        ("under_18_until","DBH",18), ("under_19_until","DBI",19), ("under_21_until","DBJ",21)
    ]:
        if u_key in parsed and dob:
            u_date   = date.fromisoformat(parsed[u_key])
            expected = date(dob.year + u_yrs, dob.month, dob.day)
            if abs((u_date - expected).days) > 2:
                warnings.append(
                    f"{u_eid}: Under-{u_yrs}-until {u_date} vs expected {expected}"
                )

    # Sex code
    if "DBC" in elements:
        sx = _clean(elements["DBC"])
        if sx not in SEX_CODES:
            issues.append(f"DBC (Sex): Invalid code '{sx}' - must be 1, 2, or 9")
        else:
            parsed["sex"] = SEX_CODES[sx]

    # Eye color
    if "DAY" in elements:
        ec = _clean(elements["DAY"]).upper()
        if ec not in EYE_COLORS:
            issues.append(f"DAY (Eye Color): '{ec}' not valid - expected {sorted(EYE_COLORS)}")
        else:
            parsed["eye_color"] = ec

    # Hair color (warning only - not all states use it)
    if "DAZ" in elements:
        hc = _clean(elements["DAZ"]).upper()
        if hc not in HAIR_COLORS:
            warnings.append(f"DAZ (Hair Color): '{hc}' not in standard set")
        else:
            parsed["hair_color"] = hc

    # Height
    if "DAU" in elements:
        ht = _clean(elements["DAU"]).upper()
        if not re.match(r"^\d{3}(IN|CM)$", ht):
            issues.append(f"DAU (Height): '{ht}' invalid - must be nnnIN or nnnCM")
        else:
            parsed["height"] = ht

    # Truncation codes
    for eid, label in [("DDE","Family"),("DDF","First"),("DDG","Middle")]:
        if eid in elements:
            tc = _clean(elements[eid]).upper()
            if tc not in TRUNC_CODES:
                issues.append(f"{eid} ({label} Name Truncation): '{tc}' invalid - T/N/U only")
            else:
                parsed[f"trunc_{label.lower()}"] = TRUNC_CODES[tc]

    # Country (warning only for unusual values)
    if "DCG" in elements:
        ct = _clean(elements["DCG"]).upper()
        if ct not in ("USA","CAN","MEX"):
            warnings.append(f"DCG (Country): Unusual value '{ct}'")
        else:
            parsed["country"] = ct

    # Compliance type
    if "DDA" in elements:
        cmp = _clean(elements["DDA"]).upper()
        if cmp not in COMPLIANCE_TYPES:
            warnings.append(f"DDA (Compliance): '{cmp}' not F or N")
        else:
            parsed["compliance_type"] = COMPLIANCE_TYPES[cmp]

    # Limited duration
    if "DDD" in elements:
        ld = _clean(elements["DDD"])
        if ld not in ("0","1"):
            warnings.append(f"DDD (Limited Duration): '{ld}' invalid")
        else:
            parsed["limited_duration"] = ld == "1"

    # DL-specific fields
    if subfile_type == "DL":
        if "DCA" in elements:
            parsed["vehicle_class"] = _clean(elements["DCA"])
        if "DCD" in elements:
            endc = _clean(elements["DCD"]).upper()
            parsed["endorsements"] = endc
            if endc not in ("NONE","N",""):
                for ec in re.split(r"[,\s]+", endc):
                    if ec and ec not in STD_ENDORSEMENTS:
                        warnings.append(f"DCD: Endorsement '{ec}' is state-specific")
        if "DCB" in elements:
            rst = _clean(elements["DCB"]).upper()
            parsed["restrictions"] = rst
            if rst not in ("NONE","N",""):
                for rc in re.split(r"[,\s]+", rst):
                    if rc and rc not in STD_RESTRICTIONS:
                        warnings.append(f"DCB: Restriction '{rc}' is state-specific")

    # Postal code - AAMVA pads DAK to 11 chars with spaces
    if "DAK" in elements:
        raw_pk = elements["DAK"]
        pk = re.sub(r"[\s\-]", "", raw_pk.strip())
        if pk:  # non-empty after stripping
            us_ok = bool(re.match(r"^\d{5,9}$", pk))
            ca_ok = bool(re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", pk, re.I))
            if not (us_ok or ca_ok):
                issues.append(f"DAK (Postal Code): Unexpected format '{raw_pk.strip()}'")
            else:
                parsed["postal_code"] = raw_pk.strip()

    # Weight
    if "DAW" in elements:
        wt = _clean(elements["DAW"])
        if re.match(r"^\d{3}$", wt):
            parsed["weight_lbs"] = wt

    # ** PRIMARY ANTI-FAKE: IIN <-> DAJ state cross-check **
    # This is kept as a hard ISSUE - a mismatched IIN/state is the #1 fake signal
    if "DAJ" in elements and iin in AAMVA_IIN:
        expected = AAMVA_IIN[iin][1].upper()
        actual   = _clean(elements["DAJ"]).upper()
        if actual and actual != expected:
            issues.append(
                f"CRITICAL STATE MISMATCH: IIN {iin} belongs to "
                f"{AAMVA_IIN[iin][0]} ({expected}) but DAJ says '{actual}'. "
                f"Primary indicator of a fabricated barcode."
            )

    # Mandatory fields: WARNING only (real IDs omit optional fields)
    if ELEMENT_CATALOG:
        for mk, ml in mandatory_for_version(version, subfile_type).items():
            if mk not in elements:
                warnings.append(f"Field {mk} ({ml}) absent (optional on some state IDs)")

    # Per-element catalog validation
    for eid, val in elements.items():
        issues.extend(_validate_element(eid, val))

    # Name / address fields
    for eid, key in [
        ("DCS","last_name"),("DAC","first_name"),("DAD","middle_name"),
        ("DAG","address_street"),("DAI","address_city"),("DAJ","address_state"),
        ("DAQ","license_number"),("DCF","document_discriminator"),("DCU","name_suffix"),
    ]:
        if eid in elements:
            parsed[key] = _clean(elements[eid])

    if "DBK" in elements:
        parsed["organ_donor"] = _clean(elements["DBK"]) == "1"
    if "DBL" in elements:
        parsed["veteran"] = _clean(elements["DBL"]) == "1"

    return issues, warnings, parsed


# -- Main validator entry point ------------------------------------------------
def validate_aamva_raw(raw: str) -> dict:
    result = {
        "valid":        False,
        "score":        0,
        "issues":       [],
        "warnings":     [],
        "fields":       {},
        "header":       {},
        "subfiles":     [],
        "subfile_type": None,
    }

    if not raw or not raw.strip():
        result["issues"].append("Empty barcode data")
        return result

    # Header
    header = parse_header(raw)
    if not header:
        result["issues"].append(
            "AAMVA header signature not found. "
            "Genuine AAMVA barcodes begin with '@' + control chars + 'ANSI' + 6-digit IIN. "
            "This barcode does not comply with AAMVA Annex D structure."
        )
        return result

    result["header"] = {k: v for k, v in header.items() if k != "header_end"}
    iin     = header["iin"]
    version = header["aamva_version"]

    # IIN registry
    if iin in AAMVA_IIN:
        j = AAMVA_IIN[iin]
        result["fields"]["issuer"] = {
            "iin": iin, "state": j[0], "abbreviation": j[1], "country": j[2]
        }
    else:
        result["issues"].append(
            f"IIN '{iin}' is NOT in the AAMVA jurisdiction registry. "
            f"All genuine US/Canadian DL/IDs use a registered IIN. "
            f"Strong indicator of a fabricated barcode."
        )

    # Version
    if not (1 <= version <= 10):
        result["issues"].append(f"AAMVA version {version} outside valid range 1-10")
    else:
        result["fields"]["aamva_version"] = version

    # Subfile directory
    dir_entries = parse_subfile_directory(raw, header["header_end"], header["num_entries"])
    if not dir_entries:
        result["warnings"].append("Subfile directory not parsed; using text-scan fallback")

    # Build subfile list
    subfiles_to_process = []
    if dir_entries:
        for entry in dir_entries:
            sf_type  = entry["type"]
            sf_label = SUBFILE_TYPES.get(sf_type, f"Subfile {sf_type}")
            o, l = entry["offset"], entry["length"]
            if o > 0 and l > 0 and o + l <= len(raw):
                body = raw[o: o + l]
            else:
                idx  = raw.find(sf_type, header["header_end"])
                body = raw[idx:] if idx != -1 else ""
            subfiles_to_process.append((sf_type, sf_label, body))
    else:
        for sf_type, sf_label in SUBFILE_TYPES.items():
            idx = raw.find(sf_type, header["header_end"])
            if idx != -1:
                subfiles_to_process.append((sf_type, sf_label, raw[idx:]))

    # Validate each subfile
    primary_found = False
    processed     = set()

    for sf_type, sf_label, body in subfiles_to_process:
        if sf_type in processed or not body:
            continue
        processed.add(sf_type)

        elements = parse_elements(body)
        sf_info  = {
            "type": sf_type, "label": sf_label,
            "elements": elements, "issues": [], "warnings": []
        }

        if sf_type in ("DL", "ID"):
            primary_found = True
            result["subfile_type"] = sf_type
            si, sw, sp = validate_elements(elements, version, iin, sf_type)
            sf_info["issues"]   = si
            sf_info["warnings"] = sw
            result["issues"]   += si
            result["warnings"] += sw
            result["fields"].update(sp)
            result["fields"]["elements"] = elements
        elif sf_type.startswith("Z"):
            for eid, val in elements.items():
                if eid in JURISDICTION_ELEMENTS:
                    sf_info[f"parsed_{eid}"] = {
                        "label": JURISDICTION_ELEMENTS[eid], "value": val
                    }

        result["subfiles"].append(sf_info)

    if not primary_found:
        result["issues"].append(
            "No DL or ID subfile found. "
            "Every genuine AAMVA barcode must contain a DL or ID subfile."
        )

    # Score: -10 per hard issue, -2 per warning, -5 if expired
    expired = any("EXPIRED" in w for w in result["warnings"])
    score   = 100 - len(result["issues"]) * 10 - len(result["warnings"]) * 2 - (5 if expired else 0)
    result["score"] = max(0, min(100, score))
    result["valid"] = len(result["issues"]) == 0
    return result
