"""
AAMVA DL/ID PDF417 Barcode Parser & Validator
Implements AAMVA DL/ID Card Design Standard versions 1-10 (2000-2025).

Anti-fake detection layers (all preserved, false-positive causes fixed):
  1.  AAMVA header signature - flexible match for all real scanner output variants
  2.  IIN registry validation - all 50 states, DC, territories, CA provinces
  3.  IIN <-> DAJ state cross-match (ISSUE only - primary counterfeit signal)
  4.  Cross-date logical impossibility checks (ISSUE only)
  5.  Field format validation per Annex B
  6.  Mandatory field presence (WARNING - real IDs omit optional fields)
  7.  Subfile directory structure integrity
  8.  Element length bounds (ISSUE only when max is defined and exceeded)
  9.  Endorsement/restriction/vehicle class codes (WARNING - state codes vary)
  10. Compliance type and REAL ID indicator
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
    # Minimal fallbacks so the validator still works without the data module
    ELEMENT_CATALOG = {}
    SUBFILE_TYPES = {"DL": "Driver License", "ID": "Identification Card",
                     "ZA": "Arizona Jurisdiction", "ZC": "California Jurisdiction",
                     "ZF": "Florida Jurisdiction", "ZG": "Georgia Jurisdiction",
                     "ZI": "Illinois Jurisdiction", "ZM": "Michigan Jurisdiction",
                     "ZN": "Minnesota Jurisdiction", "ZO": "Ohio Jurisdiction",
                     "ZT": "Texas Jurisdiction", "ZV": "Virginia Jurisdiction",
                     "ZW": "Washington Jurisdiction"}
    JURISDICTION_ELEMENTS = {}
    EYE_COLORS  = {"BLK","BLU","BRN","GRY","GRN","HAZ","MAR","PNK","DIC","UNK"}
    HAIR_COLORS = {"BAL","BLK","BLN","BRO","GRY","RED","SDY","WHI","UNK"}
    SEX_CODES   = {"1": "Male", "2": "Female", "9": "Unknown"}
    TRUNC_CODES = {"T": "Truncated", "N": "Not Truncated", "U": "Unknown"}
    COMPLIANCE_TYPES = {"F": "Fully Compliant", "N": "Non-Compliant"}
    WEIGHT_RANGES = {str(i): f"Range {i}" for i in range(10)}
    STD_VEHICLE_CLASSES = set("ABCDM")
    STD_ENDORSEMENTS    = {"H","L","N","P","S","T","X","NONE"}
    STD_RESTRICTIONS    = {"B","C","D","E","F","G","I","J","K","L","M","N",
                           "O","V","W","NONE"}
    def mandatory_for_version(v, st): return {}
    def element_label(eid): return eid

# ── Complete IIN registry (Annex D, Table D-1) --------------------------------
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

# ── Header regex: covers ALL documented variants real scanners produce ----------
# Spec: @<LF><RS><CR>ANSI  (0x0A 0x1C 0x0D)
# Real scanners also emit: @<CR><LF>, @<LF>, @<CR>, bare @ANSI
# We accept any combination of whitespace/control chars between @ and ANSI.
AAMVA_HEADER_RE = re.compile(
    r"@[\x00-\x1f\s]*ANSI\s*(\d{6})(\d{2})(\d{2})(\d{2})",
    re.DOTALL
)

# Subfile directory entry (Annex D): <2-char type><4-digit offset><4-digit length>
SUBFILE_DIR_RE = re.compile(r"([A-Z]{2})(\d{4})(\d{4})")


# ── Annex C: Version-aware date parser ----------------------------------------
def _clean_field(val: str) -> str:
    """Strip whitespace, null bytes, and padding that real IDs embed in fields."""
    return val.strip().rstrip("\x00").strip()


def parse_date(val: str, version: int):
    """Parse AAMVA date field. Returns (date, None) or (None, error_string)."""
    val = _clean_field(val)
    # Some states embed trailing spaces inside date fields — strip digits only
    digits = re.sub(r"\D", "", val)
    if len(digits) != 8:
        return None, f"Invalid date '{val}' — need exactly 8 digits, got {len(digits)}"
    try:
        if version <= 8:    # MMDDCCYY  (v1-v8)
            mm, dd, ccyy = digits[0:2], digits[2:4], digits[4:8]
        else:               # CCYYMMDD  (v9-v10)
            ccyy, mm, dd = digits[0:4], digits[4:6], digits[6:8]
        return date(int(ccyy), int(mm), int(dd)), None
    except ValueError as e:
        return None, str(e)


# ── Annex D: Header parser ----------------------------------------------------
def parse_header(raw: str):
    """Parse the AAMVA file header. Returns dict or None."""
    m = AAMVA_HEADER_RE.search(raw)
    if not m:
        return None
    return {
        "iin":                  m.group(1),
        "aamva_version":        int(m.group(2)),
        "jurisdiction_version": int(m.group(3)),
        "num_entries":          int(m.group(4)),
        "header_end":           m.end(),
    }


# ── Annex D: Subfile directory parser -----------------------------------------
def parse_subfile_directory(raw: str, header_end: int, num_entries: int):
    directory_text = raw[header_end: header_end + (num_entries * 10) + 30]
    entries = []
    for m in SUBFILE_DIR_RE.finditer(directory_text):
        entries.append({"type": m.group(1), "offset": int(m.group(2)), "length": int(m.group(3))})
        if len(entries) >= num_entries:
            break
    return entries


# ── Element parser ------------------------------------------------------------
def parse_elements(text: str):
    """
    Extract data elements. Handles LF, CR, and CR+LF line endings.
    A data element line is: <3-char ELEMENT-ID><value> with no separator.
    """
    elements = {}
    # Normalise all line endings to LF first
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for line in text.split("\n"):
        line = line.strip()
        if len(line) >= 4 and re.match(r"^[A-Z]{3}", line[:3]):
            key = line[:3]
            val = line[3:]  # DO NOT strip val here - some values have leading spaces
            # But do strip null bytes and trailing whitespace
            val = val.rstrip("\x00").rstrip()
            if val and key not in elements:  # first occurrence wins per Annex D
                elements[key] = val
    return elements


# ── Element-level validator ---------------------------------------------------
def validate_element_value(eid: str, val: str, version: int):
    """
    Validate a single element value against Annex B catalog.
    Returns list of ISSUE strings. Only raises issues on hard violations.
    Jurisdiction-specific and unknown elements are silently skipped.
    """
    issues = []
    meta = ELEMENT_CATALOG.get(eid)
    if not meta:
        return []  # Unknown / jurisdiction-specific: never flag

    max_len = meta.get("max", 0)
    min_len = meta.get("min", 0)
    presence = meta.get("presence", "O")
    etype = meta.get("type", "A")

    # Length: only flag if OVER max (under-min is already caught by mandatory check)
    if max_len > 0 and len(val) > max_len:
        issues.append(
            f"{eid} ({meta.get('label', eid)}): value length {len(val)} exceeds max {max_len}"
        )

    # Numeric fields must be digits
    if etype == "N":
        clean = re.sub(r"[\s\x00]", "", val)
        if not re.match(r"^\d+$", clean):
            issues.append(f"{eid} ({meta.get('label', eid)}): must be numeric, got '{val}'")

    return issues


# ── Full element set validator ------------------------------------------------
def validate_elements(elements: dict, version: int, iin: str, subfile_type: str):
    issues, warnings, parsed = [], [], {}

    # ── Date fields -----------------------------------------------------------
    date_fields = {
        "DBB": ("Date of Birth",     "date_of_birth"),
        "DBA": ("Expiry Date",       "expiry_date"),
        "DBD": ("Issue Date",        "issue_date"),
        "DDB": ("Card Revision Date","card_revision_date"),
        "DDC": ("HAZMAT Expiry",     "hazmat_expiry"),
        "DBH": ("Under 18 Until",    "under_18_until"),
        "DBI": ("Under 19 Until",    "under_19_until"),
        "DBJ": ("Under 21 Until",    "under_21_until"),
        "PAB": ("Permit Expiry",     "permit_expiry"),
        "PAD": ("Permit Issue",      "permit_issue"),
    }
    for eid, (label, key) in date_fields.items():
        if eid in elements:
            d, err = parse_date(elements[eid], version)
            if err:
                issues.append(f"{eid} ({label}): {err}")
            else:
                parsed[key] = d.isoformat()

    # ── Cross-date sanity (hard impossibility = ISSUE; soft = WARNING) --------
    dob = date.fromisoformat(parsed["date_of_birth"]) if "date_of_birth" in parsed else None
    iss = date.fromisoformat(parsed["issue_date"])     if "issue_date"     in parsed else None
    exp = date.fromisoformat(parsed["expiry_date"])    if "expiry_date"    in parsed else None
    today = date.today()

    if dob:
        age = (today - dob).days // 365
        if age < 14 or age > 120:
            # Warning not issue — DOB field decode may legitimately differ by state
            warnings.append(f"DBB: Unusual age calculated — {age} years")
        if iss and iss < dob:
            issues.append("DBD: Issue date is before date of birth — logically impossible")
        if exp and (exp - dob).days // 365 > 125:
            issues.append("DBA: Expiry >125 years after DOB — impossible")

    if iss and iss > today:
        issues.append("DBD: Issue date is in the future — impossible on a genuine document")

    if exp and exp < today:
        # EXPIRED is a WARNING not a hard issue — real expired IDs still have valid barcodes
        warnings.append("DBA: Document is EXPIRED")

    if exp and iss and exp <= iss:
        issues.append("DBA: Expiry date is not after issue date — impossible")

    # Under-age date markers consistency (WARNING only)
    for u_key, u_eid, u_years in [
        ("under_18_until","DBH",18),("under_19_until","DBI",19),("under_21_until","DBJ",21)
    ]:
        if u_key in parsed and dob:
            u_date = date.fromisoformat(parsed[u_key])
            expected = date(dob.year + u_years, dob.month, dob.day)
            if abs((u_date - expected).days) > 2:  # 2-day tolerance for leap years
                warnings.append(
                    f"{u_eid}: Under-{u_years}-until ({u_date}) does not match "
                    f"DOB + {u_years}y ({expected})"
                )

    # ── Sex code --------------------------------------------------------------
    if "DBC" in elements:
        sx = _clean_field(elements["DBC"])
        if sx not in SEX_CODES:
            issues.append(f"DBC (Sex): Invalid code '{sx}' — must be 1, 2, or 9")
        else:
            parsed["sex"] = SEX_CODES[sx]

    # ── Eye color -------------------------------------------------------------
    if "DAY" in elements:
        ec = _clean_field(elements["DAY"]).upper()
        if ec not in EYE_COLORS:
            issues.append(f"DAY (Eye Color): '{ec}' not in AAMVA set {sorted(EYE_COLORS)}")
        else:
            parsed["eye_color"] = ec

    # ── Hair color (WARNING only — not all states encode this) ----------------
    if "DAZ" in elements:
        hc = _clean_field(elements["DAZ"]).upper()
        if hc not in HAIR_COLORS:
            warnings.append(f"DAZ (Hair Color): '{hc}' not in AAMVA set")
        else:
            parsed["hair_color"] = hc

    # ── Height ---------------------------------------------------------------
    if "DAU" in elements:
        ht = _clean_field(elements["DAU"]).upper()
        if not re.match(r"^\d{3}(IN|CM)$", ht):
            issues.append(f"DAU (Height): Invalid format '{ht}' — must be nnnIN or nnnCM")
        else:
            parsed["height"] = ht

    # ── Weight ---------------------------------------------------------------
    if "DAW" in elements:
        wt = _clean_field(elements["DAW"])
        if not re.match(r"^\d{3}$", wt):
            warnings.append(f"DAW (Weight lbs): Format '{wt}' — expected 3 digits")
        else:
            parsed["weight_lbs"] = wt
    if "DAV" in elements:
        wt = _clean_field(elements["DAV"])
        if not re.match(r"^\d{3}$", wt):
            warnings.append(f"DAV (Weight kg): Format '{wt}' — expected 3 digits")
        else:
            parsed["weight_kg"] = wt

    # ── Truncation codes ------------------------------------------------------
    for eid, label in [("DDE","Family Name"),("DDF","First Name"),("DDG","Middle Name")]:
        if eid in elements:
            tc = _clean_field(elements[eid]).upper()
            if tc not in TRUNC_CODES:
                issues.append(f"{eid} ({label} Truncation): Invalid code '{tc}' — T/N/U only")
            else:
                parsed[f"trunc_{label.lower().replace(' ','_')}"] = TRUNC_CODES[tc]

    # ── Country ---------------------------------------------------------------
    if "DCG" in elements:
        ct = _clean_field(elements["DCG"]).upper()
        if ct not in ("USA","CAN","MEX"):
            warnings.append(f"DCG (Country): Unusual value '{ct}'")
        else:
            parsed["country"] = ct

    # ── Compliance type -------------------------------------------------------
    if "DDA" in elements:
        cmp = _clean_field(elements["DDA"]).upper()
        if cmp not in COMPLIANCE_TYPES:
            warnings.append(f"DDA (Compliance Type): '{cmp}' not F or N")
        else:
            parsed["compliance_type"] = COMPLIANCE_TYPES[cmp]

    # ── Limited duration ------------------------------------------------------
    if "DDD" in elements:
        ld = _clean_field(elements["DDD"])
        if ld not in ("0","1"):
            warnings.append(f"DDD (Limited Duration): Invalid value '{ld}'")
        else:
            parsed["limited_duration"] = ld == "1"

    # ── Vehicle class (DL only) -----------------------------------------------
    if subfile_type == "DL" and "DCA" in elements:
        parsed["vehicle_class"] = _clean_field(elements["DCA"])

    # ── Endorsements (WARNING only — states use their own codes) --------------
    if subfile_type == "DL" and "DCD" in elements:
        endc = _clean_field(elements["DCD"]).upper()
        parsed["endorsements"] = endc
        if endc and endc not in ("NONE","N",""):
            for ec in re.split(r"[,\s]+", endc):
                if ec and ec not in STD_ENDORSEMENTS:
                    warnings.append(f"DCD: Endorsement '{ec}' is state-specific (not in AAMVA standard set)")

    # ── Restrictions (WARNING only) -------------------------------------------
    if subfile_type == "DL" and "DCB" in elements:
        rstc = _clean_field(elements["DCB"]).upper()
        parsed["restrictions"] = rstc
        if rstc and rstc not in ("NONE","N",""):
            for rc in re.split(r"[,\s]+", rstc):
                if rc and rc not in STD_RESTRICTIONS:
                    warnings.append(f"DCB: Restriction '{rc}' is state-specific (not in AAMVA standard set)")

    # ── Postal code -----------------------------------------------------------
    # AAMVA spec: DAK is 11 chars, padded with spaces (e.g. '90021      ' or '90210-4567 ')
    if "DAK" in elements:
        raw_pk = elements["DAK"]
        pk = re.sub(r"[\s\-]", "", raw_pk.strip())
        us_ok = bool(re.match(r"^\d{5,9}$", pk))
        ca_ok = bool(re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", pk, re.I))
        if not (us_ok or ca_ok) and len(pk) > 0:
            # Only flag if not empty and not plausibly valid
            issues.append(f"DAK (Postal Code): Unexpected format '{raw_pk.strip()}'")
        else:
            parsed["postal_code"] = raw_pk.strip()

    # ── IIN <-> DAJ cross-check (PRIMARY anti-fake — always ISSUE) ------------
    if "DAJ" in elements and iin in AAMVA_IIN:
        expected_abbr = AAMVA_IIN[iin][1].upper()
        barcode_state = _clean_field(elements["DAJ"]).upper()
        if barcode_state and barcode_state != expected_abbr:
            issues.append(
                f"CRITICAL STATE MISMATCH: IIN {iin} is registered to "
                f"{AAMVA_IIN[iin][0]} ({expected_abbr}), "
                f"but DAJ field says '{barcode_state}'. "
                f"Primary indicator of a fabricated barcode."
            )

    # ── Mandatory fields: WARNING only (real IDs legitimately omit optional) --
    if ELEMENT_CATALOG:  # only if data module loaded
        mandatory = mandatory_for_version(version, subfile_type)
        for mk, ml in mandatory.items():
            if mk not in elements:
                warnings.append(
                    f"Optional AAMVA field {mk} ({ml}) is absent "
                    f"(some states omit this even on genuine IDs)"
                )

    # ── Per-element catalog validation ----------------------------------------
    for eid, val in elements.items():
        ev_issues = validate_element_value(eid, val, version)
        issues.extend(ev_issues)

    # ── Name / address fields -------------------------------------------------
    for eid, key in [("DCS","last_name"),("DAC","first_name"),("DAD","middle_name")]:
        if eid in elements:
            parsed[key] = _clean_field(elements[eid])
    for eid, key in [("DAG","address_street"),("DAI","address_city"),
                     ("DAJ","address_state"),("DAQ","license_number"),
                     ("DCU","name_suffix"),("DCF","document_discriminator")]:
        if eid in elements:
            parsed[key] = _clean_field(elements[eid])

    if "DBK" in elements:
        parsed["organ_donor"] = _clean_field(elements["DBK"]) == "1"
    if "DBL" in elements:
        parsed["veteran"] = _clean_field(elements["DBL"]) == "1"

    return issues, warnings, parsed


# ── Main validator ------------------------------------------------------------
def validate_aamva_raw(raw: str):
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

    # ── Header ----------------------------------------------------------------
    header = parse_header(raw)
    if not header:
        result["issues"].append(
            "AAMVA header signature not found. "
            "Genuine AAMVA barcodes begin with @[control chars]ANSI + 6-digit IIN. "
            "This barcode does not comply with AAMVA Annex D header structure."
        )
        return result

    result["header"] = {k: v for k, v in header.items() if k != "header_end"}
    iin     = header["iin"]
    version = header["aamva_version"]

    # ── IIN registry ---------------------------------------------------------
    if iin in AAMVA_IIN:
        j = AAMVA_IIN[iin]
        result["fields"]["issuer"] = {"iin": iin, "state": j[0], "abbreviation": j[1], "country": j[2]}
    else:
        result["issues"].append(
            f"IIN '{iin}' is NOT in the AAMVA jurisdiction registry. "
            f"All genuine US/Canadian DL/IDs use a registered IIN. "
            f"Strong indicator of a fabricated barcode."
        )

    # ── AAMVA version ---------------------------------------------------------
    if not (1 <= version <= 10):
        result["issues"].append(f"AAMVA version {version} outside valid range 1–10")
    else:
        result["fields"]["aamva_version"] = version

    # ── Subfile directory ----------------------------------------------------
    dir_entries = parse_subfile_directory(raw, header["header_end"], header["num_entries"])
    if not dir_entries:
        result["warnings"].append("Subfile directory not parsed; using text-scan fallback")

    # ── Build subfile list ---------------------------------------------------
    subfiles_to_process = []
    if dir_entries:
        for entry in dir_entries:
            sf_type  = entry["type"]
            sf_label = SUBFILE_TYPES.get(sf_type, f"Subfile ({sf_type})")
            offset, length = entry["offset"], entry["length"]
            if offset > 0 and length > 0 and offset + length <= len(raw):
                body = raw[offset: offset + length]
            else:
                idx  = raw.find(sf_type, header["header_end"])
                body = raw[idx:] if idx != -1 else ""
            subfiles_to_process.append((sf_type, sf_label, body))
    else:
        # Fallback: scan for all known subfile markers
        for sf_type, sf_label in SUBFILE_TYPES.items():
            idx = raw.find(sf_type, header["header_end"])
            if idx != -1:
                subfiles_to_process.append((sf_type, sf_label, raw[idx:]))

    # ── Validate each subfile ------------------------------------------------
    primary_found = False
    processed     = set()

    for sf_type, sf_label, body in subfiles_to_process:
        if sf_type in processed or not body:
            continue
        processed.add(sf_type)

        elements = parse_elements(body)
        sf_info  = {"type": sf_type, "label": sf_label, "elements": elements,
                    "issues": [], "warnings": []}

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
                    sf_info[f"parsed_{eid}"] = {"label": JURISDICTION_ELEMENTS[eid], "value": val}

        result["subfiles"].append(sf_info)

    if not primary_found:
        result["issues"].append(
            "No DL or ID subfile found. Every genuine AAMVA barcode must contain a DL or ID subfile."
        )

    # ── Score -----------------------------------------------------------------
    # issues: -10 each (hard violations)
    # warnings: -2 each (soft / informational)
    # Expired doc: -5 extra (it's real but expired)
    expired_penalty = 5 if any("EXPIRED" in w for w in result["warnings"]) else 0
    score = 100 - len(result["issues"]) * 10 - len(result["warnings"]) * 2 - expired_penalty
    result["score"] = max(0, min(100, score))
    result["valid"] = len(result["issues"]) == 0
    return result
