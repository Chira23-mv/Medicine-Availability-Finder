# MedFind — Medicine Availability Finder

A Flask + SQLite prototype for searching medicine listings and viewing pharmacy-reported stock quantities and update timestamps. Includes a pharmacy inventory update screen and review-only alternative-product listings.

## Features
- Search medicine name, brand, strength, or dosage form
- Show participating pharmacy addresses, reported quantity, and last update
- Update inventory quantities (zero means reported out of stock)
- SQLite database initialized automatically with clearly labeled demo data
- JSON search endpoint at `/api/search?q=paracetamol`
- Health endpoint at `/health`
- Responsive HTML/CSS interface

## Run on macOS

```bash
cd medfind
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser. Open http://127.0.0.1:5000/inventory to update sample stock. The SQLite file `medfind.db` is created automatically on first run.

## Project structure

```text
medfind/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   └── inventory.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## Important limitations before real-world use
- Seed data is fictional demo data. It is not a live pharmacy network.
- The inventory page is intentionally unauthenticated for local demonstration. Before deployment, add user accounts, password hashing, pharmacy-scoped authorization, CSRF protection, rate limiting, secure secrets, and audit logs.
- Do not store patient information. Use HTTPS and an appropriate privacy/security review if you add accounts or external integrations.
- Alternative listings are only flags for pharmacist review. They are not claims of therapeutic equivalence or instructions to substitute medication.
- Stock is only as current as the last pharmacy update. Users should contact the pharmacy before travelling.

## GitHub
Do not commit `.venv/`, secrets, or the generated `medfind.db`. GitHub Pages cannot run a Flask backend; use a Python-capable host if you later want the search and database to work publicly.
