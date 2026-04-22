import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Customs Data Extractor", layout="wide")
st.title("📄 Bill of Entry Data Extractor")
st.write("Upload your PDF to extract BE details, Invoices, and Item tables.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
        
        # 1. Extract General Header Data using Regex
        def find_val(pattern, text):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else "Not Found"

        header_data = {
            "BE No": find_val(r"BE No\n.*?(\d+)", full_text),
            "BE Date": find_val(r"BE Date\n.*?(\d{2}/\d{2}/\d{4})", full_text),
            "IGM No": find_val(r"1\.IGM NO\s+(\d+)", full_text),
            "MAWB No": find_val(r"6\.MAWB NO\s+([A-Z0-7 ]+)", full_text),
            "Gross Weight": find_val(r"G\.WT \(KGS\)\n.*?(\d+)", full_text),
        }

        # Display Header Data
        st.subheader("📌 General Details")
        st.json(header_data)

        # 2. Extract Tables (Invoices and Items)
        st.subheader("📦 Extracted Tables")
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                df = pd.DataFrame(table[1:], columns=table[0]) # Use first row as header
                st.write(f"Table from Page {i+1}")
                st.dataframe(df)
                
                # Download button for each table
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download as CSV", csv, f"table_p{i+1}_{j}.csv", "text/csv")