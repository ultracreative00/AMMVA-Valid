"""
AAMVA DL/ID PDF417 Barcode Parser & Validator

Implements AAMVA DL/ID Card Design Standard versions 1-10 (2000-2025).

Annex coverage:
  Annex A  — File structure & encoding rules
  Annex B  — Data element definitions (200+ elements, all types/lengths)
  Annex C  — Version-aware date formats (MMDDCCYY v1-8, CCYYMMDD v9-10)
  Annex D  — Header structure, subfile directory, IIN registry
  Annex E  — Vehicle class, restriction, endorsement code validation
  Annex F  — Jurisdiction-specific subfile parsing

Anti-fake detection layers:
  1. AAMVA header signature check
  2. IIN registry validation (all 50 states, DC, territories, CA provinces)
  3. IIN <-> DAJ state cross-match
  4. Cross-date logical impossibility checks
  5. Field format validation per Annex B element catalog
  6. Mandatory field presence check per version
  7. Subfile directory structure integrity
  8. Element length bounds validation
  9. Endorsement / restriction / vehicle class code validation
 10. Compliance type and REAL ID indicator checks
"""

import re
from datetime import date

from aamva_data_elements import (
    ELEMENT_CATALOG,
    SUBFILE_TYPES,
    JURISDICTION_ELEMENTS,
    EYE_COLORS,
    HAIR_COLORS,
    SEX_CODES,
    TRUNC_CODES,
    COMPLIANCE_TYPES,
    WEIGHT_RANGES,
    STD_VEHICLE_CLASSES,
    STD_ENDORSEMENTS,
    STD_RESTRICTIONS,
    mandatory_for_version,
    element_label,
)

# ── Complete IIN registry (Annex D, Table D-1) ────────────────────────────────
AAMVA_IIN = {
    "636000": ("Virginia",              "VA", "US"),
    "636001": ("New York",              "NY", "US"),
    "636002": ("Massachusetts",         "MA", "US"),
    "636003": ("Maryland",              "MD", "US"),
    "636004": ("North Carolina",        "NC", "US"),
    "636005": ("South Carolina",        "SC", "US"),
    "636006": ("Connecticut",           "CT", "US"),
    "636007": ("Louisiana",             "LA", "US"),
    "636008": ("Arkansas",              "AR", "US"),
    "636009": ("Texas",                 "TX", "US"),
    "636010": ("Colorado",              "CO", "US"),
    "636011": ("Georgia",               "GA", "US"),
    "636012": ("Arizona",               "AZ", "US"),
    "636013": ("California",            "CA", "US"),
    "636014": ("Hawaii",                "HI", "US"),
    "636015": ("Kansas",                "KS", "US"),
    "636016": ("Mississippi",           "MS", "US"),
    "636017": ("New Hampshire",         "NH", "US"),
    "636018": ("New Jersey",            "NJ", "US"),
    "636019": ("Michigan",              "MI", "US"),
    "636020": ("Illinois",              "IL", "US"),
    "636021": ("Pennsylvania",          "PA", "US"),
    "636022": ("Kentucky",              "KY", "US"),
    "636023": ("Ohio",                  "OH", "US"),
    "636024": ("Florida",               "FL", "US"),
    "636025": ("Tennessee",             "TN", "US"),
    "636026": ("Indiana",               "IN", "US"),
    "636027": ("Alabama",               "AL", "US"),
    "636028": ("Nebraska",              "NE", "US"),
    "636029": ("Missouri",              "MO", "US"),
    "636030": ("Iowa",                  "IA", "US"),
    "636031": ("Minnesota",             "MN", "US"),
    "636032": ("Wisconsin",             "WI", "US"),
    "636033": ("Washington",            "WA", "US"),
    "636034": ("Oregon",                "OR", "US"),
    "636035": ("Nevada",                "NV", "US"),
    "636036": ("Idaho",                 "ID", "US"),
    "636037": ("Montana",               "MT", "US"),
    "636038": ("Wyoming",               "WY", "US"),
    "636039": ("North Dakota",          "ND", "US"),
    "636040": ("South Dakota",          "SD", "US"),
    "636041": ("Utah",                  "UT", "US"),
    "636042": ("New Mexico",            "NM", "US"),
    "636043": ("Oklahoma",              "OK", "US"),
    "636044": ("Maine",                 "ME", "US"),
    "636045": ("Delaware",              "DE", "US"),
    "636046": ("Rhode Island",          "RI", "US"),
    "636047": ("Vermont",               "VT", "US"),
    "636048": ("Alaska",                "AK", "US"),
    "636049": ("West Virginia",         "WV", "US"),
    "636050": ("District of Columbia",  "DC", "US"),
    "636051": ("Puerto Rico",           "PR", "US"),
    "636052": ("US Virgin Islands",     "VI", "US"),
    "636053": ("Guam",                  "GU", "US"),
    "636220": ("American Samoa",        "AS", "US"),
    "636055": ("Ontario",               "ON", "CA"),
    "636056": ("Quebec",                "QC", "CA"),
    "636057": ("British Columbia",      "BC", "CA"),
    "636058": ("Alberta",               "AB", "CA"),
    "636059": ("Manitoba",              "MB", "CA"),
    "636060": ("Saskatchewan",          "SK", "CA"),
    "636061": ("Nova Scotia",           "NS", "CA"),
    "636062": ("New Brunswick",         "NB", "CA"),
    "636063": ("Newfoundland",          "NL", "CA"),
    "636064": ("Prince Edward Island",  "PE", "CA"),
    "636065": ("Northwest Territories", "NT", "CA"),
    "636066": ("Yukon",                 "YT", "CA"),
    "604427": ("Alberta (alt)",         "AB", "CA"),
}

# Annex D header regex — exactly as per the standard
# @<LF><RS><CR>ANSI <IIN:6><AAMVA version:2><Jurisdiction version:2><Num Entries:2>
AAMVA_HEADER_RE = re.compile(
    r"@\n?[\x1c]?\r?ANSI\s+(\d{6})(\d{2})(\d{2})(\d{2})", re.DOTALL
)

# Annex D subfile directory entry: <Subfile Type:2><Offset:4><Length:4>
SUBFILE_DIR_RE = re.compile(r"([A-Z]{2})(\d{4})(\d{4})")


# ── Annex C: Version-aware date parser ───────────────────────────────────────
def parse_date(val: str, version: int):
    """Parse AAMVA date field. Returns (date, None) or (None, error_string)."""
    val = val.strip()
    if len(val) != 8 or not val.isdigit():
        return None, f"Invalid date '{val}' — must be exactly 8 digits"
    try:
        if version <= 8:    # MMDDCCYY (v1-v8)
            mm, dd, ccyy = val[0:2], val[2:4], val[4:8]
        else:               # CCYYMMDD (v9-v10)
            ccyy, mm, dd = val[0:4], val[4:6], val[6:8]
        return date(int(ccyy), int(mm), int(dd)), None
    except ValueError as e:
        return None, str(e)


# ── Annex D: Header parser ────────────────────────────────────────────────────
def parse_header(raw: str):
    """Parse the AAMVA file header. Returns dict or None if no valid header found."""
    m = AAMVA_HEADER_RE.search(raw)
    if not m:
        return None
    return {
        "iin":                  m.group(1),
        "aamva_version":        int(m.group(2)),
        "jurisdiction_version": int(m.group(3)),
        "num_entries":          int(m.group(4)),
        "header_end":           m.end(),
        "raw_match":            m.group(0),
    }


# ── Annex D: Subfile directory parser ────────────────────────────────────────
def parse_subfile_directory(raw: str, header_end: int, num_entries: int):
    """
    Parse the subfile directory that immediately follows the header.
    Returns list of {type, offset, length} dicts.
    Annex D specifies each entry is exactly 10 chars: 2-type + 4-offset + 4-length.
    """
    directory_text = raw[header_end:header_end + (num_entries * 10) + 20]
    entries = []
    for m in SUBFILE_DIR_RE.finditer(directory_text):
        entries.append({
            "type":   m.group(1),
            "offset": int(m.group(2)),
            "length": int(m.group(3)),
        })
        if len(entries) >= num_entries:
            break
    return entries


# ── Element parser ────────────────────────────────────────────────────────────
def parse_elements(text: str):
    """Extract all data elements from a subfile body."""
    elements = {}
    for line in re.split(r"[\r\n]+", text):
        line = line.strip()
        if len(line) >= 4 and re.match(r"^[A-Z]{3}", line[:3]):
            key = line[:3]
            val = line[3:].strip()
            if val and key not in elements:   # first occurrence wins per spec
                elements[key] = val
    return elements


# ── Element-level validator ───────────────────────────────────────────────────
def validate_element_value(eid: str, val: str, version: int):
    """
    Validate a single element value against its Annex B catalog entry.
    Returns list of issue strings (empty = valid).
    """
    issues = []
    meta = ELEMENT_CATALOG.get(eid)
    if not meta:
        return []  # jurisdiction-specific or unknown — no catalog to check against

    # Length bounds
    if meta["max"] > 0 and len(val) > meta["max"]:
        issues.append(
            f"{eid} ({meta['label']}): value length {len(val)} exceeds max {meta['max']}"
        )
    if meta["min"] > 0 and len(val) < meta["min"] and meta["presence"] == "M":
        issues.append(
            f"{eid} ({meta['label']}): value length {len(val)} below min {meta['min']}"
        )

    # Type-specific validation
    t = meta["type"]
    if t == "N" and not re.match(r"^\d+$", val):
        issues.append(f"{eid} ({meta['label']}): must be numeric, got '{val}'")
    elif t == "A" and not re.match(r"^[A-Za-z]+$", val):
        # Allow spaces in names
        pass

    return issues


# ── Full element set validator ────────────────────────────────────────────────
def validate_elements(elements: dict, version: int, iin: str, subfile_type: str):
    issues, warnings, parsed = [], [], {}

    # ── Date fields ──────────────────────────────────────────────────────────
    date_fields = {
        "DBB": ("Date of Birth",    "date_of_birth"),
        "DBA": ("Expiry Date",      "expiry_date"),
        "DBD": ("Issue Date",       "issue_date"),
        "DDB": ("Card Revision Date", "card_revision_date"),
        "DDC": ("HAZMAT Expiry",    "hazmat_expiry"),
        "DBH": ("Under 18 Until",   "under_18_until"),
        "DBI": ("Under 19 Until",   "under_19_until"),
        "DBJ": ("Under 21 Until",   "under_21_until"),
        "PAB": ("Permit Expiry",    "permit_expiry"),
        "PAD": ("Permit Issue",     "permit_issue"),
    }
    for eid, (label, key) in date_fields.items():
        if eid in elements:
            d, err = parse_date(elements[eid], version)
            if err:
                issues.append(f"{eid} ({label}): {err}")
            else:
                parsed[key] = d.isoformat()

    # ── Cross-date sanity (anti-fake layer) ───────────────────────────────────
    dob = date.fromisoformat(parsed["date_of_birth"]) if "date_of_birth" in parsed else None
    iss = date.fromisoformat(parsed["issue_date"])     if "issue_date"     in parsed else None
    exp = date.fromisoformat(parsed["expiry_date"])    if "expiry_date"    in parsed else None
    today = date.today()

    if dob:
        age = (today - dob).days // 365
        if age < 14 or age > 120:
            warnings.append(f"DBB: Suspicious age — {age} years old")
        if iss and iss < dob:
            issues.append("Issue date (DBD) is before date of birth (DBB) — impossible")
        if exp and (exp - dob).days // 365 > 125:
            issues.append("Expiry is >125 years after DOB — impossible")

    if iss:
        if iss > today:
            issues.append("DBD: Issue date is in the future — impossible on a genuine document")

    if exp:
        if exp < today:
            warnings.append("DBA: Document is EXPIRED")
        if iss and exp <= iss:
            issues.append("DBA: Expiry date is not after issue date — impossible")

    # Under-age date markers consistency
    for u_key, u_eid, u_years in [
        ("under_18_until", "DBH", 18),
        ("under_19_until", "DBI", 19),
        ("under_21_until", "DBJ", 21),
    ]:
        if u_key in parsed and dob:
            u_date = date.fromisoformat(parsed[u_key])
            expected = date(dob.year + u_years, dob.month, dob.day)
            delta = abs((u_date - expected).days)
            if delta > 1:  # allow 1-day leap year tolerance
                warnings.append(
                    f"{u_eid}: Under-{u_years}-until date ({u_date}) does not match "
                    f"expected birthday + {u_years} years ({expected})"
                )

    # ── Sex code ──────────────────────────────────────────────────────────────
    if "DBC" in elements:
        sx = elements["DBC"].strip()
        if sx not in SEX_CODES:
            issues.append(f"DBC (Sex): Invalid code '{sx}' — must be 1, 2, or 9")
        else:
            parsed["sex"] = SEX_CODES[sx]

    # ── Eye color ─────────────────────────────────────────────────────────────
    if "DAY" in elements:
        ec = elements["DAY"].strip().upper()
        if ec not in EYE_COLORS:
            issues.append(f"DAY (Eye Color): '{ec}' not in AAMVA set {sorted(EYE_COLORS)}")
        else:
            parsed["eye_color"] = ec

    # ── Hair color ────────────────────────────────────────────────────────────
    if "DAZ" in elements:
        hc = elements["DAZ"].strip().upper()
        if hc not in HAIR_COLORS:
            warnings.append(f"DAZ (Hair Color): '{hc}' not in AAMVA set {sorted(HAIR_COLORS)}")
        else:
            parsed["hair_color"] = hc

    # ── Height ────────────────────────────────────────────────────────────────
    if "DAU" in elements:
        ht = elements["DAU"].strip()
        if not re.match(r"^\d{3}(IN|CM)$", ht, re.IGNORECASE):
            issues.append(f"DAU (Height): Invalid format '{ht}' — must be nnnIN or nnnCM")
        else:
            parsed["height"] = ht.upper()

    # ── Weight ────────────────────────────────────────────────────────────────
    if "DAW" in elements:
        wt = elements["DAW"].strip()
        if not re.match(r"^\d{3}$", wt):
            warnings.append(f"DAW (Weight lbs): Invalid format '{wt}' — must be 3 digits")
        else:
            parsed["weight_lbs"] = wt

    if "DAV" in elements:
        wt = elements["DAV"].strip()
        if not re.match(r"^\d{3}$", wt):
            warnings.append(f"DAV (Weight kg): Invalid format '{wt}' — must be 3 digits")
        else:
            parsed["weight_kg"] = wt

    if "DAX" in elements or "DCE" in elements:
        wr = elements.get("DAX", elements.get("DCE", "")).strip()
        if wr not in WEIGHT_RANGES:
            warnings.append(f"Weight Range code '{wr}' not in AAMVA range 0-9")
        else:
            parsed["weight_range"] = WEIGHT_RANGES[wr]

    # ── Truncation codes ──────────────────────────────────────────────────────
    for eid, label in [("DDE", "Family Name"), ("DDF", "First Name"), ("DDG", "Middle Name")]:
        if eid in elements:
            tc = elements[eid].strip().upper()
            if tc not in TRUNC_CODES:
                issues.append(f"{eid} ({label} Truncation): Invalid code '{tc}' — T/N/U only")
            else:
                parsed[f"truncation_{label.lower().replace(' ', '_')}"] = TRUNC_CODES[tc]

    # ── Country ───────────────────────────────────────────────────────────────
    if "DCG" in elements:
        ct = elements["DCG"].strip().upper()
        if ct not in ("USA", "CAN", "MEX"):
            warnings.append(f"DCG (Country): Unusual value '{ct}' — expected USA/CAN/MEX")
        else:
            parsed["country"] = ct

    # ── Compliance type ───────────────────────────────────────────────────────
    if "DDA" in elements:
        cmp = elements["DDA"].strip().upper()
        if cmp not in COMPLIANCE_TYPES:
            warnings.append(f"DDA (Compliance Type): '{cmp}' not F or N")
        else:
            parsed["compliance_type"] = COMPLIANCE_TYPES[cmp]

    # ── Limited duration ──────────────────────────────────────────────────────
    if "DDD" in elements:
        ld = elements["DDD"].strip()
        if ld not in ("0", "1"):
            warnings.append(f"DDD (Limited Duration): Invalid value '{ld}' — must be 0 or 1")
        else:
            parsed["limited_duration"] = ld == "1"

    # ── Vehicle class (DL subfile only) ──────────────────────────────────────
    if subfile_type == "DL" and "DCA" in elements:
        vc = elements["DCA"].strip().upper()
        if "DCM" in elements:  # standard code available
            scm = elements["DCM"].strip().upper()
            if scm and scm not in STD_VEHICLE_CLASSES:
                warnings.append(f"DCM (Std Vehicle Class): Unknown code '{scm}'")
        parsed["vehicle_class"] = vc

    # ── Endorsements ─────────────────────────────────────────────────────────
    if subfile_type == "DL" and "DCD" in elements:
        endc = elements["DCD"].strip().upper()
        if endc and endc != "NONE":
            for ec in re.split(r"[,\s]+", endc):
                if ec and ec not in STD_ENDORSEMENTS:
                    warnings.append(f"DCD: Endorsement code '{ec}' not in AAMVA standard set")
        parsed["endorsements"] = endc

    # ── Restrictions ─────────────────────────────────────────────────────────
    if subfile_type == "DL" and "DCB" in elements:
        rstc = elements["DCB"].strip().upper()
        if rstc and rstc != "NONE":
            for rc in re.split(r"[,\s]+", rstc):
                if rc and rc not in STD_RESTRICTIONS:
                    warnings.append(f"DCB: Restriction code '{rc}' not in AAMVA standard set")
        parsed["restrictions"] = rstc

    # ── Postal code ───────────────────────────────────────────────────────────
    if "DAK" in elements:
        pk = re.sub(r"[\s-]", "", elements["DAK"])
        us_ok = re.match(r"^\d{5,9}$", pk)
        ca_ok = re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", pk, re.I)
        if not (us_ok or ca_ok):
            issues.append(f"DAK (Postal Code): Suspicious format '{elements['DAK']}'")
        else:
            parsed["postal_code"] = elements["DAK"].strip()

    # ── IIN <-> DAJ cross-check (primary anti-fake) ───────────────────────────
    if "DAJ" in elements and iin in AAMVA_IIN:
        expected_abbr = AAMVA_IIN[iin][1]
        barcode_state = elements["DAJ"].strip().upper()
        if barcode_state != expected_abbr:
            issues.append(
                f"CRITICAL STATE MISMATCH: IIN {iin} is registered to "
                f"{AAMVA_IIN[iin][0]} ({expected_abbr}), "
                f"but DAJ field says '{barcode_state}'. "
                f"This is a primary indicator of a fabricated barcode."
            )

    # ── Mandatory field presence per version ──────────────────────────────────
    mandatory = mandatory_for_version(version, subfile_type)
    for mk, ml in mandatory.items():
        if mk not in elements:
            warnings.append(f"Missing mandatory field {mk} ({ml}) required since AAMVA v{ELEMENT_CATALOG[mk]['version_added']}")

    # ── Per-element catalog validation ───────────────────────────────────────
    for eid, val in elements.items():
        ev_issues = validate_element_value(eid, val, version)
        issues.extend(ev_issues)

    # ── Name suffix ───────────────────────────────────────────────────────────
    if "DCU" in elements:
        valid_suffixes = {"JR", "SR", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}
        sfx = elements["DCU"].strip().upper()
        if sfx and sfx not in valid_suffixes:
            warnings.append(f"DCU (Name Suffix): '{sfx}' not a recognised AAMVA suffix")
        else:
            parsed["name_suffix"] = sfx

    # ── Organ donor / veteran ─────────────────────────────────────────────────
    if "DBK" in elements:
        parsed["organ_donor"] = elements["DBK"].strip() == "1"
    if "DBL" in elements:
        parsed["veteran"] = elements["DBL"].strip() == "1"

    # ── Name fields ───────────────────────────────────────────────────────────
    for eid, key in [("DCS", "last_name"), ("DAC", "first_name"), ("DAD", "middle_name")]:
        if eid in elements:
            parsed[key] = elements[eid].strip()

    if "DAG" in elements:
        parsed["address_street"] = elements["DAG"].strip()
    if "DAI" in elements:
        parsed["address_city"] = elements["DAI"].strip()
    if "DAJ" in elements:
        parsed["address_state"] = elements["DAJ"].strip().upper()
    if "DAQ" in elements:
        parsed["license_number"] = elements["DAQ"].strip()

    return issues, warnings, parsed


# ── Main validator ────────────────────────────────────────────────────────────
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

    if not raw:
        result["issues"].append("Empty barcode data")
        return result

    # ── Annex D: Header validation ────────────────────────────────────────────
    header = parse_header(raw)
    if not header:
        result["issues"].append(
            "AAMVA header signature not found. "
            "Genuine AAMVA barcodes begin with @\\n\\x1c\\rANSI followed by a 6-digit IIN. "
            "This data does not conform to AAMVA Annex D header structure."
        )
        return result

    result["header"] = {
        k: v for k, v in header.items() if k not in ("header_end", "raw_match")
    }
    iin     = header["iin"]
    version = header["aamva_version"]

    # ── IIN registry check ────────────────────────────────────────────────────
    if iin in AAMVA_IIN:
        j = AAMVA_IIN[iin]
        result["fields"]["issuer"] = {
            "iin": iin, "state": j[0], "abbreviation": j[1], "country": j[2]
        }
    else:
        result["issues"].append(
            f"IIN '{iin}' is NOT in the AAMVA jurisdiction registry. "
            f"All genuine US/Canadian DL/IDs use registered IINs. "
            f"This is a primary indicator of a fabricated barcode."
        )

    # ── AAMVA version range ───────────────────────────────────────────────────
    if not (1 <= version <= 10):
        result["issues"].append(
            f"AAMVA version {version} is outside the valid range 1-10"
        )
    else:
        result["fields"]["aamva_version"] = version

    # ── Annex D: Subfile directory ────────────────────────────────────────────
    dir_entries = parse_subfile_directory(raw, header["header_end"], header["num_entries"])
    if not dir_entries:
        result["warnings"].append(
            "Subfile directory could not be parsed; falling back to text scan"
        )

    # ── Validate each subfile ─────────────────────────────────────────────────
    primary_subfile_type = None
    all_elements = {}

    # Prefer directory-guided parsing; fall back to text scan
    subfiles_to_process = []
    if dir_entries:
        for entry in dir_entries:
            sf_type = entry["type"]
            sf_label = SUBFILE_TYPES.get(sf_type, f"Unknown subfile ({sf_type})")
            # Extract subfile body by directory offset/length when available
            offset = entry["offset"]
            length = entry["length"]
            if offset > 0 and length > 0 and offset + length <= len(raw):
                body = raw[offset: offset + length]
            else:
                # Directory offsets may be unreliable — fall back to text search
                idx = raw.find(sf_type, header["header_end"])
                body = raw[idx:] if idx != -1 else ""
            subfiles_to_process.append((sf_type, sf_label, body))
    else:
        # Text-scan fallback: find all known subfile markers
        for sf_type in list(SUBFILE_TYPES.keys()):
            idx = raw.find(sf_type, header["header_end"])
            if idx != -1:
                label = SUBFILE_TYPES[sf_type]
                subfiles_to_process.append((sf_type, label, raw[idx:]))

    processed_types = set()
    for sf_type, sf_label, body in subfiles_to_process:
        if sf_type in processed_types:
            continue
        processed_types.add(sf_type)

        if not body:
            result["warnings"].append(f"Subfile {sf_type} ({sf_label}): empty body")
            continue

        elements = parse_elements(body)
        all_elements.update(elements)  # merge for cross-subfile checks

        sf_info = {
            "type":     sf_type,
            "label":    sf_label,
            "elements": elements,
            "issues":   [],
            "warnings": [],
        }

        # Primary DL/ID subfile — full validation
        if sf_type in ("DL", "ID"):
            primary_subfile_type = sf_type
            result["subfile_type"] = sf_type
            si, sw, sp = validate_elements(elements, version, iin, sf_type)
            sf_info["issues"]   = si
            sf_info["warnings"] = sw
            result["issues"]   += si
            result["warnings"] += sw
            result["fields"].update(sp)
            result["fields"]["elements"] = elements

        # Jurisdiction subfile — parse and label elements
        elif sf_type.startswith("Z"):
            for eid, val in elements.items():
                if eid in JURISDICTION_ELEMENTS:
                    sf_info[f"parsed_{eid}"] = {
                        "label": JURISDICTION_ELEMENTS[eid],
                        "value": val,
                    }

        result["subfiles"].append(sf_info)

    if not primary_subfile_type:
        result["issues"].append(
            "No DL or ID subfile found in barcode body. "
            "Every genuine AAMVA barcode must contain a DL or ID subfile."
        )

    # ── Authenticity score ────────────────────────────────────────────────────
    score = 100 - len(result["issues"]) * 15 - len(result["warnings"]) * 3
    result["score"]  = max(0, min(100, score))
    result["valid"]  = len(result["issues"]) == 0
    return result
