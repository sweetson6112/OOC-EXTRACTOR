# 🛃 Indian Customs BE Data Extractor

A **Streamlit web application** that automatically extracts, parses, and verifies data from Indian Customs **Bill of Entry (BE)** PDF documents.

---

## 📸 Features

| Feature | Description |
|---|---|
| 📤 PDF Upload | Drag & drop any Indian Customs BE PDF |
| 📋 Header Extraction | BE No, Date, IGM, MAWB, Exchange Rate, OOC details |
| 🚢 Manifest & Container | IGM No/Date, INW Date, Container No, Seal No |
| 🧾 Invoice Summary | All 4 invoice numbers, amounts, and currencies |
| 📦 Item-wise Duties | All 19 line items with Assess Value & Total Duty |
| ✅ Cross-Verification | Auto-compares sum of item totals vs document totals (Fields 18 & 19) |
| 📊 Excel Export | Full multi-sheet Excel download |
| 📄 JSON Export | Structured JSON for downstream processing |

---

## 🗂️ Project Structure

```
be_extractor/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── config.toml     # Streamlit theme config
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/be-extractor.git
cd be-extractor
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Select your repo, branch (`main`), and file (`app.py`)
5. Click **Deploy** — live in ~2 minutes!

---

## 📋 Extracted Fields

### Header
- BE No, BE Date, BE Type
- Port Code, Exchange Rate
- Importer Name & Address, CB Name
- Country of Origin / Consignment
- Port of Loading / Shipment
- OOC No & OOC Date
- Total Assessed Value (Field 18)
- Total Duty Amount (Field 19)

### Manifest Details
- IGM No, IGM Date, INW Date
- MAWB No, MAWB Date
- Port of Loading

### Container Details
- Container Number, Seal No, FCL/LCL

### Invoice Summary
- S.No, Invoice No, Invoice Amount, Currency

### Item-wise Duties (Part III)
- Invoice No, Item No
- Item Description
- Assessed Value (Field 29)
- Total Duty (Field 30)

---

## ✅ Verification Logic

The app automatically checks:

```
Sum of all Item Assess Values (Field 29) == TOT. ASS VAL (Field 18)
Sum of all Item Total Duties  (Field 30) == TOT. AMOUNT  (Field 19)
```

A ₹5 tolerance is applied to account for rounding differences across line items.

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `pdfplumber` | PDF text extraction |
| `pandas` | Data manipulation & tables |
| `openpyxl` | Excel export |

---

## 📌 Supported BE Types

- ✅ Warehouse BE (Type W)
- ✅ Home Consumption BE (Type H)
- ✅ Multi-invoice BEs (up to 4 invoices)
- ✅ ICEGATE-generated PDFs

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/add-new-field`)
3. Commit your changes (`git commit -m 'Add new field extraction'`)
4. Push to the branch (`git push origin feature/add-new-field`)
5. Open a Pull Request
