"""
ORBITGUARD AI - Database & Telemetry Log Layer
Provides SQLite persistence for mission events, telemetry history, and maneuver decisions.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "orbitguard.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            risk_score REAL,
            status TEXT,
            metadata TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            scenario TEXT NOT NULL,
            initial_risk REAL,
            final_risk REAL,
            chosen_maneuver TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()


def log_event(event_type: str, message: str, risk_score: float = None, status: str = None, metadata: dict = None):
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()

    meta_str = json.dumps(metadata) if metadata else None
    cursor.execute("""
        INSERT INTO telemetry_logs (timestamp, event_type, message, risk_score, status, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now_str, event_type, message, risk_score, status, meta_str))

    conn.commit()
    conn.close()
    return {"timestamp": now_str, "event_type": event_type, "message": message, "risk_score": risk_score, "status": status}


def get_recent_logs(limit: int = 40):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, event_type, message, risk_score, status
        FROM telemetry_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for r in reversed(rows):
        logs.append({
            "timestamp": r["timestamp"],
            "event_type": r["event_type"],
            "message": r["message"],
            "risk_score": r["risk_score"],
            "status": r["status"]
        })
    return logs


def save_simulation_run(scenario: str, initial_risk: float, final_risk: float, chosen_maneuver: str, status: str):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO simulation_runs (timestamp, scenario, initial_risk, final_risk, chosen_maneuver, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now_str, scenario, initial_risk, final_risk, chosen_maneuver, status))
    conn.commit()
    conn.close()


def clear_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM telemetry_logs")
    conn.commit()
    conn.close()


# Initialize database schema on load
init_db()
