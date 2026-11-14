import sqlite3
import json

from pathlib import Path
from datetime import datetime, timezone


DATABASE_PATH = Path(__file__).resolve().parent.parent / "documind.db"


def initialize_database():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS document_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                document_text TEXT
            )
        """)

        columns = [
            row[1] for row in
            connection.execute("PRAGMA table_info(document_analyses)")
        ]
        if "document_text" not in columns:
            connection.execute(
                "ALTER TABLE document_analyses ADD COLUMN document_text TEXT"
            )


def save_analysis(filename, analysis, document_text=None):
    analysis_data = analysis.model_dump()

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute("""
            INSERT INTO document_analyses
            (filename, analysis_json, created_at, document_text)
            VALUES (?, ?, ?, ?)
        """, (
            filename,
            json.dumps(analysis_data),
            datetime.now(timezone.utc).isoformat(),
            document_text
        ))

        return cursor.lastrowid


def get_analysis_history():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT id, filename, analysis_json, created_at
            FROM document_analyses
            ORDER BY id DESC
        """).fetchall()

        return [
            {
                "id": row["id"],
                "filename": row["filename"],
                "analysis": json.loads(row["analysis_json"]),
                "created_at": row["created_at"]
            }
            for row in rows
        ]


def get_analysis_by_id(analysis_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            SELECT id, filename, analysis_json, created_at
            FROM document_analyses
            WHERE id = ?
        """, (analysis_id,)).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "filename": row["filename"],
            "analysis": json.loads(row["analysis_json"]),
            "created_at": row["created_at"]
        }


def get_document_text(analysis_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute("""
            SELECT document_text FROM document_analyses
            WHERE id = ?
        """, (analysis_id,)).fetchone()

        if row is None:
            return None

        return row[0]


def delete_analysis(analysis_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute("""
            DELETE FROM document_analyses
            WHERE id = ?
        """, (analysis_id,))

        return cursor.rowcount > 0
