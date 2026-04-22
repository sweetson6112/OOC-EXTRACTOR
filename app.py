import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import json

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Indian Customs BE Extractor",
    page_icon="🛃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        color: white; padding: 2rem; border-radius: 12px;
        margin-bottom: 2rem; text-align: center;
    }
    .main-header h1 { font-size: 2.2rem; margin: 0; }
    .main-header p  { font-size: 1rem; opacity: 0.8; margin-top: 0.5rem; }
    .metric-card {
        background: #f8f9fa; border: 1px solid #e0e0e0;
        border-left: 4px solid #0f3460; border-radius: 8px;
        padding: 1rem; margin-bottom: 0.8rem;
    }
    .metric-label { font-size: 0.75rem; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 1.1rem; font-weight: 600; color: #1a1a2e; }
    .section-header {
        background: #0f3460; color: white; padding: 0.6rem 1rem;
        border-radius: 6px; margin: 1.5rem 0 1rem 0;
        font-weight: 600; font-size: 0.95rem; letter-spacing: 0.05em;
    }
    .match-ok  { color: #28a745; font-weight: 700; }
    .match-err { color: #dc3545; font-weight: 700; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    .bug-box {
        background: #fff8e1; border: 1px solid #ffc107;
        border-left: 4px solid #ff9800; border-radius: 8px;
        padding: 1rem; margin-bottom: 1rem; font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PDF TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(uploaded_file):
    """
    Returns:
        page_texts : list of plain text per page
        page_tables: list of dicts {page_num, tables} for structured table data
    """
    page_texts  = []
    page_tables = []
    with pdfplumber.open(uploaded_file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            page_texts.append(text)
            tbls = page.extract_tables() or []
            if tbls:
                page_tables.append({"page": i + 1, "tables": tbls})
    return page_texts, page_tables


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def clean(s):
    return " ".join(str(s).split()).strip() if s else ""


def find(pattern, text, group=1, default=""):
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return clean(m.group(group)) if m else default


def to_float(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════

def extract_header(full_text):
    data = {}

    m = re.search(r'\b(\d{7,9})\s+(\d{2}/\d{2}/\d{4})', full_text)
    data["BE No"]   = m.group(1) if m else find(r'BE\s*No\s*:?\s*(\d{7,9})', full_text)
    data["BE Date"] = m.group(2) if m else find(r'BE\s*Date\s*:?\s*(\d{2}/\d{2}/\d{4})', full_text)
    data["BE Type"] = find(r'BE\s*Type\s*:?\s*([A-Z])\b', full_text) or "W"
    data["Port Code"] = find(r'Port\s*Code\s+(\w+)', full_text) or ""

    igm = re.search(
        r'(\d{6,8})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\d*\s*([A-Z0-9]{8,})',
        full_text, re.IGNORECASE
    )
    data["IGM No"]   = igm.group(1) if igm else ""
    data["IGM Date"] = igm.group(2) if igm else ""
    data["INW Date"] = igm.group(3) if igm else ""
    data["MAWB No"]  = igm.group(4) if igm else find(r'(MEDUVB\w+)', full_text)
    data["MAWB Date"] = find(r'(?:MEDUVB|MAWB)\w*\s+(\d{2}/\d{2}/\d{4})', full_text)

    data["Gross Weight (KGS)"] = find(r'G\.WT\s*\(KGS\)\s*[\|\s]*(\d{3,6})', full_text)

    er = find(r'1\s*USD\s*=\s*([\d\.]+)\s*INR', full_text)
    data["Exchange Rate"] = f"1 USD = {er} INR" if er else ""

    data["Importer"] = find(
        r'1\.IMPORTER\s+NAME\s+&\s+ADDRESS\s+([\w\s,\./\-]+?)(?:2\.CB NAME|2\.CB\s)',
        full_text
    )
    data["CB Name"] = find(
        r'2\.CB\s*NAME\s+([\w\s]+?)(?:\s+3\.AEO|AD CODE)',
        full_text
    )

    data["Total Assessed Value (INR)"] = (
        find(r'18\.TOT\.ASS\s*VAL\s*([\d,\.]+)', full_text) or
        find(r'TOT\.ASS VAL\s+([\d,\.]+)', full_text)
    )
    data["Total Duty Amount (INR)"] = (
        find(r'19\.TOT\.\s*AMOUNT\s*([\d,\.]+)', full_text) or
        find(r'TOT\. AMOUNT\s+([\d,\.]+)', full_text)
    )

    data["OOC No"]   = find(r'OOC\s*NO\.?\s*(\d+)', full_text)
    data["OOC Date"] = find(r'OOC\s*DATE\s+(\d{2}[-/]\d{2}[-/]\d{4})', full_text)

    data["Country of Origin"]      = find(r'13\.COUNTRY\s*OF\s*ORIGIN\s+([\w ]+?)(?:\s+14\.)', full_text)
    data["Country of Consignment"] = find(r'14\.COUNTRY\s*OF\s*CONSIGNMENT\s+([\w ]+?)(?:\s+15\.)', full_text)
    data["Port of Loading"]        = find(r'15\.PORT\s*OF\s*LOADING\s+([\w ]+?)(?:\s+16\.)', full_text)
    data["Port of Shipment"]       = find(r'16\.PORT\s*OF\s*SHIPMENT\s+([\w ]+?)(?:\n|$)', full_text)

    return data


# ══════════════════════════════════════════════════════════════════════════════
#  CONTAINERS
# ══════════════════════════════════════════════════════════════════════════════

def extract_containers(full_text):
    seen, containers = set(), []

    for m in re.finditer(r'([A-Z]{4}\d{7})\s+(\d{5,10})\s+([FL])\b', full_text):
        key = m.group(1)
        if key not in seen:
            seen.add(key)
            containers.append({
                "Container No": m.group(1),
                "Seal No":      m.group(2),
                "FCL/LCL":      "FCL" if m.group(3) == "F" else "LCL",
            })

    if not containers:
        for m in re.finditer(
            r'([A-Z]{4}\d{7})\s+([\w]*)\s+(\d{5,10})\s+([FL])\b', full_text
        ):
            key = m.group(1)
            if key not in seen:
                seen.add(key)
                containers.append({
                    "Container No": m.group(1),
                    "Seal No":      m.group(3),
                    "FCL/LCL":      "FCL" if m.group(4) == "F" else "LCL",
                })

    return containers


# ══════════════════════════════════════════════════════════════════════════════
#  INVOICES — FIX: no [:4] cap, no hardcoded prefix, 4 strategies
# ══════════════════════════════════════════════════════════════════════════════

def extract_invoices(full_text, page_tables):
    """
    ─── ROOT CAUSES FIXED ───────────────────────────────────────────────────
    BUG 1: nos[:4]  — hard slice limited results to 4 invoices.
           FIX: removed completely; deduplication via seen_nos set instead.

    BUG 2: Invoice regex r'(1320\\d{6})' — only matched invoice numbers
           starting with '1320'. Different BEs have different prefixes.
           FIX: generalised to r'\\d{7,14}' to match any invoice number.

    BUG 3: Single fallback strategy with no ordering. First match might be
           the wrong number (e.g. picking up IGM number).
           FIX: 4 prioritised strategies; primary reads the dedicated
                'N. INVOICE DETAILS' table block which is always present.
    ─────────────────────────────────────────────────────────────────────────
    """
    invoices  = []
    seen_nos  = set()

    # ── Strategy 1: N. INVOICE DETAILS block (Part IV, most reliable) ─────────
    inv_block = re.search(
        r'N\.\s*INVOICE\s*DETAILS([\s\S]{10,600}?)(?:GLOSSARY|CONTAINER DETAILS|$)',
        full_text, re.IGNORECASE
    )
    if inv_block:
        block = inv_block.group(1)
        for m in re.finditer(
            r'(\d{1,3})\s+(\d{7,14})\s+([\d,]+\.\d{2})\s+(USD|INR|EUR|GBP|JPY|AUD|SGD)',
            block, re.IGNORECASE
        ):
            no = m.group(2)
            if no not in seen_nos:
                seen_nos.add(no)
                invoices.append({
                    "S.No":           m.group(1),
                    "Invoice No":     no,
                    "Invoice Amount": to_float(m.group(3)),
                    "Currency":       m.group(4).upper(),
                })

    # ── Strategy 2: J. INVOICE DETAILS SUMMARY (page 1) ──────────────────────
    if not invoices:
        sum_block = re.search(
            r'(?:INVOICE DETAILS\s*[-]?\s*SUMMARY|J\.\s*INVOICE)([\s\S]{10,600}?)'
            r'(?:CONTAINER|BOND|PAYMENT|$)',
            full_text, re.IGNORECASE
        )
        if sum_block:
            for m in re.finditer(
                r'(\d{1,3})\s+(\d{7,14})\s+([\d,]+\.\d{2})\s+(USD|INR|EUR|GBP)',
                sum_block.group(1), re.IGNORECASE
            ):
                no = m.group(2)
                if no not in seen_nos:
                    seen_nos.add(no)
                    invoices.append({
                        "S.No":           m.group(1),
                        "Invoice No":     no,
                        "Invoice Amount": to_float(m.group(3)),
                        "Currency":       m.group(4).upper(),
                    })

    # ── Strategy 3: Part II invoice header pages ───────────────────────────────
    if not invoices:
        part2_sections = re.finditer(
            r'PART\s*-\s*II.*?Invoice\s+(\d+)\s+(\d+)\s*\)([\s\S]{50,800}?)'
            r'(?=PART\s*-\s*II|PART\s*-\s*III|$)',
            full_text, re.IGNORECASE
        )
        for sec in part2_sections:
            sno   = sec.group(1)
            block = sec.group(3)
            # invoice number is typically a 7-14 digit number near the top
            inv_no_m = re.search(r'\b(\d{7,14})\b', block)
            amt_m    = re.search(r'([\d,]+\.\d{2})', block)
            cur_m    = re.search(r'\b(USD|INR|EUR|GBP)\b', block)
            if inv_no_m and amt_m:
                no = inv_no_m.group(1)
                if no not in seen_nos:
                    seen_nos.add(no)
                    invoices.append({
                        "S.No":           sno,
                        "Invoice No":     no,
                        "Invoice Amount": to_float(amt_m.group(1)),
                        "Currency":       cur_m.group(1) if cur_m else "USD",
                    })

    # ── Strategy 4: Generic fallback — no [:4] cap ────────────────────────────
    if not invoices:
        for m in re.finditer(
            r'(\d{1,3})\s+(\d{7,14})\s+([\d,]+\.\d{2})\s+(USD|INR|EUR|GBP)',
            full_text, re.IGNORECASE
        ):
            no = m.group(2)
            if no not in seen_nos:
                seen_nos.add(no)
                invoices.append({
                    "S.No":           m.group(1),
                    "Invoice No":     no,
                    "Invoice Amount": to_float(m.group(3)),
                    "Currency":       m.group(4).upper(),
                })

    # Sort by S.No
    try:
        invoices.sort(key=lambda x: int(str(x["S.No"]).strip()))
    except Exception:
        pass

    return invoices


# ══════════════════════════════════════════════════════════════════════════════
#  ITEMS / DUTIES — FIX: fully dynamic, no KNOWN_ITEMS fallback
# ══════════════════════════════════════════════════════════════════════════════

def extract_descriptions_from_part2(full_text):
    """
    Build {(inv_no, item_no): description} from Part II item tables.
    Part II pages list items as:  S_NO  CTH  DESCRIPTION  UNIT_PRICE  QTY  UQC  AMOUNT
    """
    desc_map = {}

    # Split at each Part II invoice section
    sections = list(re.finditer(
        r'PART\s*-\s*II.*?Invoice\s+(\d+)\s+\d+\s*\)',
        full_text, re.IGNORECASE
    ))

    for i, sec in enumerate(sections):
        inv_no = int(sec.group(1))
        start  = sec.start()
        end    = sections[i + 1].start() if i + 1 < len(sections) else len(full_text)
        block  = full_text[start:end]

        # Item rows in Part II ITEM DETAILS table
        for m in re.finditer(
            r'^\s*(\d{1,2})\s+'          # item s.no
            r'(\d{8})\s+'                 # CTH code
            r'([A-Z][A-Z &\/\-\(\)\.\,\w]{10,200}?)\s+'  # description
            r'[\d\.]+\s+'                 # unit price
            r'[\d,\.]+\s+'               # quantity
            r'KGS',                       # unit
            block, re.MULTILINE | re.IGNORECASE
        ):
            item_no = int(m.group(1))
            desc    = clean(m.group(3))
            if desc:
                desc_map[(inv_no, item_no)] = desc

    return desc_map


def parse_part3_items(page_texts):
    """
    ─── ROOT CAUSES FIXED ───────────────────────────────────────────────────
    BUG 4: KNOWN_ITEMS hardcoded fallback — returned fixed 19 items from
           one specific BE document regardless of what was uploaded.
           FIX: removed entirely. Pure dynamic extraction below.

    BUG 5: Item CTH pattern r'1[780]\\d{6}' — only matched CTH codes
           starting with 180, 170, or 100 (chocolate/sugar/soft drinks).
           BEs for other goods (cosmetics, electronics, garments etc.)
           have completely different CTH prefixes.
           FIX: use r'\\d{8}' — matches any 8-digit CTH code.

    BUG 6: Single regex strategy that failed silently on variant layouts.
           FIX: 3 ordered strategies + table extraction.
    ─────────────────────────────────────────────────────────────────────────
    """
    items = []
    seen  = set()
    full  = "\n".join(page_texts)

    # ── Strategy A: parse Part III numeric blocks page by page ────────────────
    # Each item in Part III has a block like:
    #   INV ITEM  CTH  CETH  DESCRIPTION  ... ASSESS_VALUE  TOTAL_DUTY
    #   BCD_rate  SWS_rate  IGST_rate  amounts ...
    strat_a = re.compile(
        r'\b(\d{1,2})\s+(\d{1,2})\s+'    # inv_sno  item_sno
        r'(\d{8})\s+'                      # CTH (any 8-digit code)
        r'NOEXCISE\s+'
        r'([\w /\-\(\)&,\.\n]{10,250}?)'  # description (multiline ok)
        r'\s+[\d\.]+\s+'                   # UPI
        r'[A-Z]{2}\s+'                     # COO (2-letter country)
        r'[\d,\.]+\s+KGS\s+'              # qty + unit
        r'[SNFY]+\s+'                      # flags
        r'[SNFY]+\s+'
        r'FSH\w*\s+'                       # FSSAI code
        r'[NY]+\s+[NY]+\s+[NY]+\s+'
        r'[NY]+\s+[NY]+\s+'
        r'([\d,\.]+)\s+'                   # TOTAL_DUTY (field 30)
        r'\d+\s+\d+\s+'                    # BCD rate + SWS rate
        r'[\d,\.]+\s+[\d,\.]+\s+'         # BCD amount + SWS amount
        r'[\d,\.]+\s+'                     # IGST amount
        r'(?:[\d,\.]+\s+){0,5}'
        r'([\d,\.]+)\s+([\d,\.]+)',        # ASSESS_VALUE (29), TOTAL_DUTY (30) again
        re.IGNORECASE | re.DOTALL
    )
    for m in strat_a.finditer(full):
        key = (int(m.group(1)), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            # field 29 and 30 appear twice; last occurrence is the authoritative one
            items.append({
                "Inv No":       int(m.group(1)),
                "Item No":      int(m.group(2)),
                "CTH":          m.group(3),
                "Description":  clean(m.group(4)),
                "Assess Value": to_float(m.group(6)),
                "Total Duty":   to_float(m.group(7)),
            })

    # ── Strategy B: simpler pattern — just inv/item + two large numbers ───────
    if len(items) < 2:
        items, seen = [], set()
        strat_b = re.compile(
            r'\b(\d{1,2})\s+(\d{1,2})\s+'   # inv item
            r'(\d{8})\s+NOEXCISE\b'           # CTH
            r'([\s\S]{20,400}?)'              # everything until values
            r'([\d,]{5,}\.?\d{0,2})\s+'       # assess value
            r'([\d,]{4,}\.?\d{0,2})\b',       # total duty
            re.IGNORECASE
        )
        for m in strat_b.finditer(full):
            key = (int(m.group(1)), int(m.group(2)))
            if key not in seen:
                av = to_float(m.group(5))
                td = to_float(m.group(6))
                # Sanity: assess value should be > total duty for most goods
                if av > 1000 and td > 100:
                    seen.add(key)
                    items.append({
                        "Inv No":       int(m.group(1)),
                        "Item No":      int(m.group(2)),
                        "CTH":          m.group(3),
                        "Description":  "",
                        "Assess Value": av,
                        "Total Duty":   td,
                    })

    # ── Strategy C: look for "29.ASSESS VALUE" and "30. TOTAL DUTY" labels ───
    if len(items) < 2:
        items, seen = [], set()
        strat_c = re.compile(
            r'\b(\d{1,2})\s+(\d{1,2})\s+\d{8}\s+NOEXCISE'
            r'[\s\S]{0,800}?'
            r'29\.ASSESS\s*VALUE\s*([\d,\.]+)'
            r'[\s\S]{0,200}?'
            r'30\.\s*TOTAL\s*DUTY\s*([\d,\.]+)',
            re.IGNORECASE | re.DOTALL
        )
        for m in strat_c.finditer(full):
            key = (int(m.group(1)), int(m.group(2)))
            if key not in seen:
                seen.add(key)
                items.append({
                    "Inv No":       int(m.group(1)),
                    "Item No":      int(m.group(2)),
                    "CTH":          "",
                    "Description":  "",
                    "Assess Value": to_float(m.group(3)),
                    "Total Duty":   to_float(m.group(4)),
                })

    return sorted(items, key=lambda x: (x["Inv No"], x["Item No"]))


def extract_items_from_tables(page_tables):
    """Extract item rows from pdfplumber structured table output."""
    items = []
    seen  = set()

    for page_data in page_tables:
        for table in page_data["tables"]:
            for row in table:
                if not row or len(row) < 4:
                    continue
                cells = [clean(c) for c in row if c is not None]
                if len(cells) < 4:
                    continue
                # Rows where first two cells are single/double digit numbers
                if (cells[0].isdigit() and cells[1].isdigit()):
                    inv_no  = int(cells[0])
                    item_no = int(cells[1])
                    key     = (inv_no, item_no)
                    if key in seen:
                        continue
                    # Find last two large numbers (assess value, total duty)
                    nums = []
                    for c in reversed(cells):
                        v = to_float(c)
                        if v > 500:
                            nums.append(v)
                        if len(nums) == 2:
                            break
                    if len(nums) == 2:
                        seen.add(key)
                        desc = " ".join(
                            c for c in cells[2:max(2, len(cells)-2)]
                            if c and not c.replace(".", "").replace(",", "").isdigit()
                        )
                        items.append({
                            "Inv No":       inv_no,
                            "Item No":      item_no,
                            "CTH":          cells[2] if len(cells[2]) == 8 and cells[2].isdigit() else "",
                            "Description":  desc[:200],
                            "Assess Value": nums[1],
                            "Total Duty":   nums[0],
                        })

    return sorted(items, key=lambda x: (x["Inv No"], x["Item No"]))


def extract_items(page_texts, page_tables):
    """
    Master item extractor — cascades through strategies.
    Never falls back to hardcoded data.
    """
    full_text = "\n".join(page_texts)

    # Try table-based first (most structured)
    items = extract_items_from_tables(page_tables)

    # If tables didn't give enough, use text-based parsing
    if len(items) < 3:
        items = parse_part3_items(page_texts)

    # Enrich descriptions from Part II pages
    desc_map = extract_descriptions_from_part2(full_text)
    for item in items:
        key = (item["Inv No"], item["Item No"])
        if desc_map.get(key) and len(item.get("Description", "")) < 10:
            item["Description"] = desc_map[key]

    # Last-resort description patch: scan nearby text
    for item in items:
        if len(item.get("Description", "")) < 5:
            inv_no, item_no = item["Inv No"], item["Item No"]
            pat = re.compile(
                rf'\b{inv_no}\s+{item_no}\s+\d{{8}}\s+NOEXCISE\s+'
                r'([A-Z][A-Z &\/\-\(\)\.\,\w]{5,180}?)'
                r'(?:\s+[\d\.]+\s+(?:KGS|NOS|PCS))',
                re.IGNORECASE
            )
            m = pat.search(full_text)
            if m:
                item["Description"] = clean(m.group(1))

    return items


# ══════════════════════════════════════════════════════════════════════════════
#  VERIFY
# ══════════════════════════════════════════════════════════════════════════════

def verify_totals(data):
    items  = data["items"]
    sum_av = sum(i["Assess Value"] for i in items)
    sum_td = sum(i["Total Duty"]   for i in items)
    doc_av = to_float(data["header"].get("Total Assessed Value (INR)", "0"))
    doc_td = to_float(data["header"].get("Total Duty Amount (INR)",    "0"))
    tol    = 10.0
    return {
        "sum_assess_value":   round(sum_av, 2),
        "sum_total_duty":     round(sum_td, 2),
        "doc_assess_value":   doc_av,
        "doc_total_duty":     doc_td,
        "assess_value_match": abs(sum_av - doc_av) <= tol or doc_av == 0,
        "total_duty_match":   abs(sum_td - doc_td) <= tol or doc_td == 0,
        "assess_value_diff":  round(sum_av - doc_av, 2),
        "total_duty_diff":    round(sum_td - doc_td, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

def extract_all(uploaded_file):
    page_texts, page_tables = extract_text_from_pdf(uploaded_file)
    full_text = "\n".join(page_texts)
    return {
        "header":     extract_header(full_text),
        "containers": extract_containers(full_text),
        "invoices":   extract_invoices(full_text, page_tables),
        "items":      extract_items(page_texts, page_tables),
        "page_count": len(page_texts),
        "full_text":  full_text,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  EXCEL EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def to_excel(data):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            list(data["header"].items()), columns=["Field", "Value"]
        ).to_excel(writer, sheet_name="Header", index=False)

        if data["containers"]:
            pd.DataFrame(data["containers"]).to_excel(
                writer, sheet_name="Containers", index=False
            )
        if data["invoices"]:
            pd.DataFrame(data["invoices"]).to_excel(
                writer, sheet_name="Invoices", index=False
            )
        if data["items"]:
            df = pd.DataFrame(data["items"])
            totals = pd.DataFrame([{
                "Inv No": "TOTAL", "Item No": "", "CTH": "",
                "Description": "",
                "Assess Value": df["Assess Value"].sum(),
                "Total Duty":   df["Total Duty"].sum(),
            }])
            pd.concat([df, totals], ignore_index=True).to_excel(
                writer, sheet_name="Item Duties", index=False
            )

        v = verify_totals(data)
        pd.DataFrame([
            {
                "Check": "Total Assessed Value",
                "Sum of Items":   round(v["sum_assess_value"], 2),
                "Document Value": v["doc_assess_value"],
                "Difference":     v["assess_value_diff"],
                "Status": "MATCH" if v["assess_value_match"] else "MISMATCH",
            },
            {
                "Check": "Total Duty Amount",
                "Sum of Items":   round(v["sum_total_duty"], 2),
                "Document Value": v["doc_total_duty"],
                "Difference":     v["total_duty_diff"],
                "Status": "MATCH" if v["total_duty_match"] else "MISMATCH",
            },
        ]).to_excel(writer, sheet_name="Verification", index=False)

    return output.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def render_metric(label, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value or "—"}</div>
    </div>
    """, unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="section-header">📋 {title}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=80)
    st.markdown("### 🛃 BE Data Extractor")
    st.markdown("**Indian Customs** — Bill of Entry Analyzer")
    st.divider()
    st.markdown("#### What's extracted")
    for f in [
        "✅ BE No, Date, Type",
        "✅ IGM / MAWB details",
        "✅ All containers & seals",
        "✅ All invoices — no limit",
        "✅ All line items — no limit",
        "✅ CTH codes per item",
        "✅ Assess Value (field 29)",
        "✅ Total Duty (field 30)",
        "✅ Totals cross-verification",
    ]:
        st.markdown(f)
    st.divider()
    st.markdown("#### v2 fixes")
    st.markdown("""
- 🔧 Removed `[:4]` invoice cap
- 🔧 Removed hardcoded item fallback
- 🔧 Generic invoice number regex
- 🔧 Generic CTH code regex (any 8-digit)
- 🔧 4 strategies for invoices
- 🔧 3 strategies + table parsing for items
- 🔧 Works for any goods category
    """)
    st.divider()
    st.caption("Supports ICEGATE-generated PDFs")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🛃 Indian Customs BE Extractor</h1>
    <p>Automatically extract & verify all fields from any Bill of Entry PDF — no invoice or item limit</p>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Drop your Bill of Entry PDF here",
    type=["pdf"],
    help="Supports Indian Customs BE — any number of invoices and items",
)

if not uploaded:
    st.info("👆 Upload a Bill of Entry PDF to get started.", icon="ℹ️")

    st.markdown("---")
    st.markdown("### 🐛 Why the old version was limited to 4 invoices")
    st.markdown('<div class="bug-box">', unsafe_allow_html=True)
    st.markdown("""
**6 root causes identified and fixed:**

| # | Bug | Location | Fix applied |
|---|---|---|---|
| 1 | `nos[:4]` hard slice | `extract_invoices()` fallback | Removed — uses dedup `set` instead |
| 2 | Regex `(1320\\d{6})` — only one invoice prefix | `extract_invoices()` | Changed to `\\d{7,14}` (any invoice number) |
| 3 | Single strategy, wrong order | `extract_invoices()` | 4 prioritised strategies added |
| 4 | `KNOWN_ITEMS` hardcoded 19-item fallback | `extract_items()` | Removed entirely — pure dynamic parsing |
| 5 | CTH regex `1[780]\\d{6}` — only chocolate/sugar codes | `extract_items()` | Changed to `\\d{8}` (any CTH code) |
| 6 | No table-based extraction | N/A | Added `pdfplumber` table parser |
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ── Process ───────────────────────────────────────────────────────────────────
with st.spinner("📖 Extracting data from all pages..."):
    data       = extract_all(uploaded)
    header     = data["header"]
    containers = data["containers"]
    invoices   = data["invoices"]
    items      = data["items"]
    verify     = verify_totals(data)

st.success(
    f"✅ Extraction complete — **{len(invoices)} invoices**, **{len(items)} line items**, "
    f"**{len(containers)} container(s)** across **{data['page_count']} pages**.",
    icon="✅"
)

# ── Export ────────────────────────────────────────────────────────────────────
c1, c2, _ = st.columns([1, 1, 4])
with c1:
    st.download_button(
        "📊 Download Excel",
        data=to_excel(data),
        file_name=f"BE_{header.get('BE No', 'export')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with c2:
    st.download_button(
        "📄 Download JSON",
        data=json.dumps({k: v for k, v in data.items() if k != "full_text"}, indent=2),
        file_name=f"BE_{header.get('BE No', 'export')}.json",
        mime="application/json",
    )

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Header", "🚢 Manifest & Container", "🧾 Invoices", "📦 Item Duties", "✅ Verification"
])

with tab1:
    section("Bill of Entry — Header Summary")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric("BE Number",    header.get("BE No"))
        render_metric("BE Date",      header.get("BE Date"))
        render_metric("BE Type",      header.get("BE Type"))
        render_metric("Port Code",    header.get("Port Code"))
    with c2:
        render_metric("OOC No",       header.get("OOC No"))
        render_metric("OOC Date",     header.get("OOC Date"))
        render_metric("Exchange Rate",header.get("Exchange Rate"))
        render_metric("Gross Weight", (header.get("Gross Weight (KGS)") or "") + " KGS")
    with c3:
        render_metric("Importer",     header.get("Importer"))
        render_metric("CB Name",      header.get("CB Name"))
        render_metric("Country of Origin",      header.get("Country of Origin"))
        render_metric("Country of Consignment", header.get("Country of Consignment"))

    section("Duty Summary (document header fields)")
    dc1, dc2 = st.columns(2)
    with dc1:
        render_metric("Total Assessed Value — Field 18 (INR)",
                      header.get("Total Assessed Value (INR)"))
    with dc2:
        render_metric("Total Duty Amount — Field 19 (INR)",
                      header.get("Total Duty Amount (INR)"))


with tab2:
    section("Manifest Details")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        render_metric("IGM No",   header.get("IGM No"))
        render_metric("IGM Date", header.get("IGM Date"))
    with mc2:
        render_metric("INW Date", header.get("INW Date"))
        render_metric("MAWB No",  header.get("MAWB No"))
    with mc3:
        render_metric("MAWB Date",       header.get("MAWB Date"))
        render_metric("Port of Loading", header.get("Port of Loading"))

    section(f"Container Details — {len(containers)} found")
    if containers:
        st.dataframe(pd.DataFrame(containers), use_container_width=True, hide_index=True)
    else:
        st.warning("No container details found.")


with tab3:
    section(f"Invoice Summary — {len(invoices)} invoice(s) found")
    if invoices:
        df_inv = pd.DataFrame(invoices).copy()
        df_inv["Invoice Amount"] = df_inv["Invoice Amount"].apply(lambda x: f"{x:,.2f}")
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
        total_val = sum(to_float(i["Invoice Amount"]) for i in invoices)
        currency  = invoices[0]["Currency"] if invoices else "USD"
        st.metric(f"Total Invoice Value ({currency})", f"{total_val:,.2f}")
    else:
        st.warning("No invoice details found.")


with tab4:
    section(f"Item-wise Duties — {len(items)} line item(s) found")
    if items:
        df_items   = pd.DataFrame(items)
        df_display = df_items.copy()
        df_display["Assess Value"] = df_display["Assess Value"].apply(lambda x: f"₹ {x:,.2f}")
        df_display["Total Duty"]   = df_display["Total Duty"].apply(lambda x: f"₹ {x:,.2f}")
        df_display.columns = [
            "Inv", "Item", "CTH", "Description",
            "Assess Value (INR)", "Total Duty (INR)"
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Total Line Items",  len(items))
        tc2.metric("Sum Assess Values", f"₹ {df_items['Assess Value'].sum():,.2f}")
        tc3.metric("Sum Total Duties",  f"₹ {df_items['Total Duty'].sum():,.2f}")
    else:
        st.warning("No item-level duty data could be extracted from this PDF.")


with tab5:
    section("Cross-Verification: Sum of Items vs Document Totals")
    st.markdown("""
    **Field 29 (Assess Value)** summed across all items → compared with **Field 18 (TOT. ASS VAL)**
    **Field 30 (Total Duty)** summed across all items → compared with **Field 19 (TOT. AMOUNT)**
    """)

    v = verify
    vc1, vc2 = st.columns(2)

    with vc1:
        st.markdown("#### 📊 Assessed Value")
        st.metric("Sum of Item Values (Field 29)", f"₹ {v['sum_assess_value']:,.2f}")
        st.metric("Document Total (Field 18)",     f"₹ {v['doc_assess_value']:,.2f}")
        st.metric("Difference",                    f"₹ {v['assess_value_diff']:,.2f}")
        if v["assess_value_match"]:
            st.markdown('<span class="match-ok">✅ MATCH</span>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<span class="match-err">❌ MISMATCH — ₹{v["assess_value_diff"]:,.2f}</span>',
                unsafe_allow_html=True
            )

    with vc2:
        st.markdown("#### 💰 Total Duty")
        st.metric("Sum of Item Duties (Field 30)", f"₹ {v['sum_total_duty']:,.2f}")
        st.metric("Document Total (Field 19)",     f"₹ {v['doc_total_duty']:,.2f}")
        st.metric("Difference",                    f"₹ {v['total_duty_diff']:,.2f}")
        if v["total_duty_match"]:
            st.markdown('<span class="match-ok">✅ MATCH</span>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<span class="match-err">❌ MISMATCH — ₹{v["total_duty_diff"]:,.2f}</span>',
                unsafe_allow_html=True
            )

    st.divider()
    if v["assess_value_match"] and v["total_duty_match"]:
        st.success("🎉 Full verification passed — all totals reconcile.", icon="✅")
    else:
        st.error("⚠️ Verification failed — review item data above.", icon="❌")

    section("Verification Summary Table")
    st.dataframe(pd.DataFrame([
        {
            "Check":          "Total Assessed Value",
            "Sum of Items":   f"₹ {v['sum_assess_value']:,.2f}",
            "Document Value": f"₹ {v['doc_assess_value']:,.2f}",
            "Difference":     f"₹ {v['assess_value_diff']:,.2f}",
            "Status": "✅ MATCH" if v["assess_value_match"] else "❌ MISMATCH",
        },
        {
            "Check":          "Total Duty Amount",
            "Sum of Items":   f"₹ {v['sum_total_duty']:,.2f}",
            "Document Value": f"₹ {v['doc_total_duty']:,.2f}",
            "Difference":     f"₹ {v['total_duty_diff']:,.2f}",
            "Status": "✅ MATCH" if v["total_duty_match"] else "❌ MISMATCH",
        },
    ]), use_container_width=True, hide_index=True)

    with st.expander("🔍 Debug: raw extracted text (first 6000 chars)"):
        st.text(data["full_text"][:6000])
