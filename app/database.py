import sqlite3
import json
import hashlib
import hmac
import os

from pathlib import Path
from datetime import datetime, timezone


DATABASE_PATH = Path(__file__).resolve().parent.parent / "documind.db"


def _initialize_analyses_table():
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS document_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                document_text TEXT,
                user_id INTEGER
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
        if "user_id" not in columns:
            connection.execute(
                "ALTER TABLE document_analyses ADD COLUMN user_id INTEGER"
            )

        connection.execute(
            "DELETE FROM document_analyses WHERE user_id IS NULL"
        )


def initialize_database():
    _initialize_analyses_table()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def save_analysis(user_id, filename, analysis, document_text=None):
    analysis_data = analysis.model_dump()

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute("""
            INSERT INTO document_analyses
            (filename, analysis_json, created_at, document_text, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            filename,
            json.dumps(analysis_data),
            datetime.now(timezone.utc).isoformat(),
            document_text,
            user_id
        ))

        return cursor.lastrowid


def get_analysis_history(user_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT id, filename, analysis_json, created_at
            FROM document_analyses
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        return [
            {
                "id": row["id"],
                "filename": row["filename"],
                "analysis": json.loads(row["analysis_json"]),
                "created_at": row["created_at"]
            }
            for row in rows
        ]


def get_analysis_by_id(analysis_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute("""
            SELECT id, filename, analysis_json, created_at
            FROM document_analyses
            WHERE id = ? AND user_id = ?
        """, (analysis_id, user_id)).fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "filename": row["filename"],
            "analysis": json.loads(row["analysis_json"]),
            "created_at": row["created_at"]
        }


def get_document_text(analysis_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute("""
            SELECT document_text FROM document_analyses
            WHERE id = ? AND user_id = ?
        """, (analysis_id, user_id)).fetchone()

        if row is None:
            return None

        return row[0]


def delete_analysis(analysis_id, user_id):
    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute("""
            DELETE FROM document_analyses
            WHERE id = ? AND user_id = ?
        """, (analysis_id, user_id))

        return cursor.rowcount > 0


def _hash_password(password, salt):
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1
    )


def register_user(username, password):
    username = username.strip().lower()
    salt = os.urandom(16)
    stored = salt.hex() + ":" + _hash_password(password, salt).hex()

    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.execute("""
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
            """, (username, stored, datetime.now(timezone.utc).isoformat()))
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def verify_user(username, password):
    username = username.strip().lower()

    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute("""
            SELECT id, password_hash FROM users WHERE username = ?
        """, (username,)).fetchone()

    if row is None:
        return None

    salt_hex, hash_hex = row[1].split(":")
    candidate = _hash_password(password, bytes.fromhex(salt_hex))

    if hmac.compare_digest(candidate, bytes.fromhex(hash_hex)):
        return row[0]

    return None
