from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "medfind.db"
app = Flask(__name__)
app.secret_key = "change-this-development-secret-before-deployment"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS pharmacies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            strength TEXT DEFAULT '',
            form TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pharmacy_id INTEGER NOT NULL REFERENCES pharmacies(id) ON DELETE CASCADE,
            medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
            updated_at TEXT NOT NULL,
            UNIQUE(pharmacy_id, medicine_id)
        );
        CREATE TABLE IF NOT EXISTS alternatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
            alternative_medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
            review_note TEXT DEFAULT 'Requires pharmacist review',
            UNIQUE(medicine_id, alternative_medicine_id),
            CHECK(medicine_id != alternative_medicine_id)
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM pharmacies").fetchone()[0]
        if count == 0:
            db.executemany("INSERT INTO pharmacies(name,address,phone,created_at) VALUES(?,?,?,?)", [
                ("City Care Pharmacy", "12 Lake Road, Coimbatore", "+91 90000 10001", now_iso()),
                ("Wellness Meds", "44 Main Street, Coimbatore", "+91 90000 10002", now_iso()),
                ("Green Cross Pharmacy", "8 Market Road, Coimbatore", "+91 90000 10003", now_iso()),
            ])
            meds = [
                ("Paracetamol", "500 mg", "Tablet", "Generic", "Sample listing; verify product details with pharmacist."),
                ("Cetirizine", "10 mg", "Tablet", "Generic", "Sample listing; verify product details with pharmacist."),
                ("ORS", "Standard sachet", "Powder", "Generic", "Oral rehydration salts; sample listing."),
                ("Ibuprofen", "200 mg", "Tablet", "Generic", "Sample listing; check suitability with a healthcare professional."),
                ("Vitamin C", "500 mg", "Tablet", "Generic", "Sample listing; verify product details with pharmacist."),
                ("Paracetamol", "650 mg", "Tablet", "Generic", "Different strength; do not assume interchangeable."),
            ]
            db.executemany("INSERT INTO medicines(name,strength,form,brand,description) VALUES(?,?,?,?,?)", meds)
            med_rows = db.execute("SELECT id,name,strength FROM medicines ORDER BY id").fetchall()
            pharmacy_rows = db.execute("SELECT id FROM pharmacies ORDER BY id").fetchall()
            quantities = [8, 0, 15, 4, 12, 5, 0, 7, 3, 0, 9, 6, 11, 2, 0, 4, 10, 1]
            idx = 0
            for p in pharmacy_rows:
                for m in med_rows:
                    qty = quantities[idx % len(quantities)]
                    db.execute("INSERT OR IGNORE INTO inventory(pharmacy_id,medicine_id,quantity,updated_at) VALUES(?,?,?,?)",
                               (p["id"], m["id"], qty, now_iso()))
                    idx += 1
            # These are only possible alternatives to be reviewed by a pharmacist, not substitution advice.
            paracetamol_500 = db.execute("SELECT id FROM medicines WHERE name='Paracetamol' AND strength='500 mg'").fetchone()[0]
            paracetamol_650 = db.execute("SELECT id FROM medicines WHERE name='Paracetamol' AND strength='650 mg'").fetchone()[0]
            cetirizine = db.execute("SELECT id FROM medicines WHERE name='Cetirizine'").fetchone()[0]
            vitamin_c = db.execute("SELECT id FROM medicines WHERE name='Vitamin C'").fetchone()[0]
            db.executemany("INSERT OR IGNORE INTO alternatives(medicine_id,alternative_medicine_id,review_note) VALUES(?,?,?)", [
                (paracetamol_500, paracetamol_650, "Different strength: pharmacist must assess; not an automatic substitute."),
                (cetirizine, vitamin_c, "Demo relationship only; not a therapeutic equivalent. Pharmacist review required."),
            ])


def fetch_medicine_results(search=""):
    with get_db() as db:
        if search:
            medicines = db.execute("""
                SELECT * FROM medicines
                WHERE name LIKE ? OR brand LIKE ? OR strength LIKE ? OR form LIKE ?
                ORDER BY name, strength
            """, tuple([f"%{search}%"] * 4)).fetchall()
        else:
            medicines = db.execute("SELECT * FROM medicines ORDER BY name, strength LIMIT 12").fetchall()
        results = []
        for med in medicines:
            stock = db.execute("""
                SELECT i.quantity, i.updated_at, p.name AS pharmacy_name, p.address, p.phone
                FROM inventory i JOIN pharmacies p ON p.id=i.pharmacy_id
                WHERE i.medicine_id=? ORDER BY (i.quantity > 0) DESC, p.name
            """, (med["id"],)).fetchall()
            alts = db.execute("""
                SELECT m.name, m.strength, m.form, a.review_note
                FROM alternatives a JOIN medicines m ON m.id=a.alternative_medicine_id
                WHERE a.medicine_id=? ORDER BY m.name
            """, (med["id"],)).fetchall()
            results.append({"medicine": dict(med), "pharmacies": [dict(x) for x in stock], "alternatives": [dict(x) for x in alts]})
        return results


@app.route("/")
def index():
    q = request.args.get("q", "").strip()[:100]
    return render_template("index.html", q=q, results=fetch_medicine_results(q))


@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    with get_db() as db:
        if request.method == "POST":
            try:
                pharmacy_id = int(request.form.get("pharmacy_id", ""))
                medicine_id = int(request.form.get("medicine_id", ""))
                quantity = int(request.form.get("quantity", ""))
                if quantity < 0 or quantity > 1_000_000:
                    raise ValueError
                pharmacy = db.execute("SELECT id FROM pharmacies WHERE id=?", (pharmacy_id,)).fetchone()
                medicine = db.execute("SELECT id FROM medicines WHERE id=?", (medicine_id,)).fetchone()
                if not pharmacy or not medicine:
                    raise ValueError
                db.execute("""
                    INSERT INTO inventory(pharmacy_id,medicine_id,quantity,updated_at) VALUES(?,?,?,?)
                    ON CONFLICT(pharmacy_id,medicine_id) DO UPDATE SET quantity=excluded.quantity, updated_at=excluded.updated_at
                """, (pharmacy_id, medicine_id, quantity, now_iso()))
                flash("Inventory updated successfully.", "success")
                return redirect(url_for("inventory"))
            except (ValueError, TypeError):
                flash("Please choose a pharmacy and medicine, and enter a valid quantity (0 or more).", "error")
        pharmacies = db.execute("SELECT * FROM pharmacies ORDER BY name").fetchall()
        medicines = db.execute("SELECT * FROM medicines ORDER BY name,strength").fetchall()
        rows = db.execute("""
            SELECT i.id, i.quantity, i.updated_at, p.name AS pharmacy_name, m.name AS medicine_name,
                   m.strength, m.form
            FROM inventory i JOIN pharmacies p ON p.id=i.pharmacy_id
            JOIN medicines m ON m.id=i.medicine_id
            ORDER BY i.updated_at DESC LIMIT 100
        """).fetchall()
    return render_template("inventory.html", pharmacies=pharmacies, medicines=medicines, rows=rows)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()[:100]
    return jsonify(fetch_medicine_results(q))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "MedFind"})


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
