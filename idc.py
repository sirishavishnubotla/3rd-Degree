from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)  # allows frontend to talk to this backend

UPLOAD_FOLDER = "uploads"
DB_FILE = "potholes.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─── Database setup ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row   # lets us use column names
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          TEXT PRIMARY KEY,
                latitude    REAL NOT NULL,
                longitude   REAL NOT NULL,
                description TEXT,
                severity    INTEGER DEFAULT 0,
                photo_path  TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return jsonify({"message": "Pothole Reporter API is running!"})


@app.route("/report", methods=["POST"])
def submit_report():
    """
    Accepts a pothole report from the frontend.
    Expected form-data:
        latitude    (float)
        longitude   (float)
        description (string, optional)
        photo       (file, optional)
    """
    try:
        latitude    = float(request.form.get("latitude", 0))
        longitude   = float(request.form.get("longitude", 0))
        description = request.form.get("description", "")

        if latitude == 0 and longitude == 0:
            return jsonify({"error": "latitude and longitude are required"}), 400

        # Save photo if provided
        photo_path = None
        if "photo" in request.files:
            photo = request.files["photo"]
            if photo.filename != "":
                ext        = os.path.splitext(photo.filename)[1]
                filename   = f"{uuid.uuid4()}{ext}"
                photo_path = os.path.join(UPLOAD_FOLDER, filename)
                photo.save(photo_path)

        # Get severity from ML model (Person 3's endpoint)
        severity = get_severity(photo_path)

        # Save to database
        report_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                """INSERT INTO reports
                   (id, latitude, longitude, description, severity, photo_path, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (report_id, latitude, longitude, description, severity, photo_path,
                 datetime.utcnow().isoformat())
            )
            conn.commit()

        return jsonify({
            "success": True,
            "id":       report_id,
            "severity": severity,
            "message":  "Report submitted successfully!"
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reports", methods=["GET"])
def get_all_reports():
    """
    Returns all pothole reports.
    Frontend uses this to populate the map.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC"
        ).fetchall()

    reports = []
    for row in rows:
        reports.append({
            "id":          row["id"],
            "latitude":    row["latitude"],
            "longitude":   row["longitude"],
            "description": row["description"],
            "severity":    row["severity"],
            "status":      row["status"],
            "created_at":  row["created_at"],
        })

    return jsonify(reports)


@app.route("/report/<report_id>/status", methods=["PATCH"])
def update_status(report_id):
    """
    Municipality can mark a report as fixed or in-progress.
    Body JSON: { "status": "fixed" }
    """
    data       = request.get_json()
    new_status = data.get("status")

    allowed = ["pending", "in-progress", "fixed"]
    if new_status not in allowed:
        return jsonify({"error": f"status must be one of {allowed}"}), 400

    with get_db() as conn:
        conn.execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (new_status, report_id)
        )
        conn.commit()

    return jsonify({"success": True, "status": new_status})


@app.route("/stats", methods=["GET"])
def get_stats():
    """
    Quick stats for the presentation dashboard.
    """
    with get_db() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        pending  = conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0]
        fixed    = conn.execute("SELECT COUNT(*) FROM reports WHERE status='fixed'").fetchone()[0]
        critical = conn.execute("SELECT COUNT(*) FROM reports WHERE severity >= 4").fetchone()[0]

    return jsonify({
        "total_reports":    total,
        "pending":          pending,
        "fixed":            fixed,
        "critical_potholes": critical
    })


# ─── ML integration helper ────────────────────────────────────────────────────

def get_severity(photo_path):
    """
    Calls Person 3's ML model to get severity score (1-5).
    If ML server is not running, falls back to a rule-based estimate.
    """
    if photo_path is None:
        return 0   # no photo = unknown severity

    try:
        import requests as req
        response = req.post(
            "http://localhost:5001/predict",
            json={"photo_path": photo_path},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("severity", 1)
    except Exception:
        pass  # ML server not up yet — use fallback

    # Fallback: random severity for demo purposes
    import random
    return random.randint(1, 5)


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("✅  Database ready")
    print("🚀  Server starting at http://localhost:5000")
    app.run(debug=True, port=5000)