import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="BOE Extractor", layout="wide")

st.title("📄 BOE Full Extraction Tool")

uploaded_file = st.file_uploader("Upload BOE PDF", type=["pdf"])

def extract_text(pdf_file):
    text_all = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_all += text + "\n"
    return text_all

def extract(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None

if uploaded_file:

    with st.spinner("Processing PDF..."):
        text_all = extract_text(uploaded_file)

        # HEADER
        header = {
            "BE No": extract(r"BE\s*No[:\s]*([A-Z0-9]+)", text_all),
            "BE Date": extract(r"BE\s*Date[:\s]*([\d/]+)", text_all),
            "MAWB No": extract(r"MAWB\s*No[:\s]*([A-Z0-9]+)", text_all),
            "Container No": extract(r"Container\s*No[:\s]*([A-Z0-9]+)", text_all),
            "Seal": extract(r"Seal[:\s]*([A-Z0-9]+)", text_all)
        }

        header_df = pd.DataFrame(list(header.items()), columns=["Field", "Value"])

        # INVOICES
        invoice_matches = re.findall(
            r"(\d{10})\s+([\d,]+\.\d+|\d+)\s+(USD|GBP|INR)",
            text_all
        )

        invoice_df = pd.DataFrame(invoice_matches, columns=["Invoice No", "Amount", "Currency"])

        # ITEMS
        item_matches = re.findall(
            r"(\d{10})\s+(\d+)\s+(.+?)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)",
            text_all
        )

        items = []
        for inv, itemno, desc, assess, duty in item_matches:
            try:
                items.append({
                    "INVSNO": inv,
                    "ITEMSN": itemno,
                    "ITEM DESCRIPTION": desc.strip(),
                    "ASSESS VALUE": float(assess.replace(",", "")),
                    "TOTAL DUTY": float(duty.replace(",", ""))
                })
            except:
                continue

        items_df = pd.DataFrame(items)

        # TOTALS
        sum_assess = items_df["ASSESS VALUE"].sum() if not items_df.empty else 0
        sum_duty = items_df["TOTAL DUTY"].sum() if not items_df.empty else 0

        tot_ass_val = extract(r"TOT\.?\s*ASS\s*VAL[:\s]*([\d,]+\.\d+)", text_all)
        tot_amount = extract(r"TOT\.?\s*AMOUNT[:\s]*([\d,]+\.\d+)", text_all)
        fine = extract(r"FINE[:\s]*([\d,]+\.\d+)", text_all)

        def to_float(x):
            return float(x.replace(",", "")) if x else None

        tot_ass_val = to_float(tot_ass_val)
        tot_amount = to_float(tot_amount)
        fine = to_float(fine)

        validation = {
            "Sum Assess Value": sum_assess,
            "Sum Duty": sum_duty,
            "BE Total Assess Value": tot_ass_val,
            "BE Total Amount": tot_amount,
            "Fine": fine,
            "Assess Difference": (tot_ass_val - sum_assess) if tot_ass_val else None,
            "Duty Difference": (tot_amount - sum_duty) if tot_amount else None
        }

        validation_df = pd.DataFrame(list(validation.items()), columns=["Metric", "Value"])

        # DISPLAY
        st.subheader("📌 Header")
        st.dataframe(header_df, use_container_width=True)

        st.subheader("💰 Invoices")
        st.dataframe(invoice_df, use_container_width=True)

        st.subheader("📦 Items")
        st.dataframe(items_df, use_container_width=True)

        st.subheader("✅ Validation")
        st.dataframe(validation_df, use_container_width=True)

        # EXPORT EXCEL
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            header_df.to_excel(writer, sheet_name="Header", index=False)
            invoice_df.to_excel(writer, sheet_name="Invoices", index=False)
            items_df.to_excel(writer, sheet_name="Items", index=False)
            validation_df.to_excel(writer, sheet_name="Validation", index=False)

        st.download_button(
            label="📥 Download Excel",
            data=output.getvalue(),
            file_name="boe_extracted.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("✅ Extraction Complete!")