# 🛃 Indian Customs – Bill of Entry PDF Extractor

A **Streamlit** web app that parses Indian Customs **Warehouse Bill of Entry (Out-of-Charge)** PDFs
issued via ICEGATE and produces a structured Excel report.

---

## ✨ Features

| What | Details |
|---|---|
| **Multi-file upload** | Process any number of BE PDFs in one run |
| **Any number of invoices** | Works with 1–N invoices per BE |
| **Header extraction** | BE No/Date, Port, IGM, MAWB, Container, Seal, OOC, Exchange Rate, Duty totals |
| **Invoice extraction** | Invoice No, Date, Amount, Currency for every invoice |
| **Item extraction** | Inv S.No, Item S.No, CTH, Description, Qty, UPI, COO, Assess Value, Total Duty |
| **Duty reconciliation** | Compares item-level sums against `18.TOT.ASS VAL` and `19.TOT.AMOUNT`; flags mismatches and checks against `17.FINE` |
| **Excel export** | 4 formatted sheets: BE Headers · All Invoices · All Items · Duty Reconciliation |

---

## 🚀 Deploy on Streamlit Community Cloud (free)

1. **Fork / clone** this repository to your own GitHub account.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.
3. Click **"New app"**.
4. Select your repository, branch (`main`), and set **Main file path** to `app.py`.
5. Click **"Deploy"** — done! Streamlit installs `requirements.txt` automatically.

> The app will be live at `https://<your-app>.streamlit.app`

---

## 💻 Run locally

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## 📁 Repository structure

```
.
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
├── .streamlit/
│   └── config.toml      # Theme & server settings
└── README.md
```

---

## 📋 Requirements

```
streamlit>=1.32.0
pdfplumber>=0.10.3
openpyxl>=3.1.2
pandas>=2.1.0
```

---

## 📝 Notes

- The PDF must be **text-based** (not a scanned image). ICEGATE-generated BEs are always text-based.
- Item-level data is parsed from **Part-III (Duties)** pages of the BE.
- If the duty reconciliation shows a mismatch, the difference should equal the `17.FINE` field in the BE header.

---

## 📄 License

MIT – free to use and modify.
