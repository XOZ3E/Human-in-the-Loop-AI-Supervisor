# human_queue_db.py
# DB-backed human queue — CLASS VERSION (CORRECT)

import sqlite3
import json
from typing import Optional, Dict, Any
import threading

DB_PATH = "frontdesk.db"
_lock = threading.Lock()

class HumanQueueDB:
    @staticmethod
    def _get_conn():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_db():
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS help_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT NOT NULL,
                        context TEXT,
                        answer TEXT,
                        status TEXT DEFAULT 'pending',
                        answered_at TIMESTAMP
                    )
                """)
                conn.commit()

    @staticmethod
    def add_question(question: str, context: str = "") -> int:
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO help_requests (question, context, status) VALUES (?, ?, 'pending')",
                    (question, context)
                )
                conn.commit()
                return cur.lastrowid

    @staticmethod
    def get_question(question_id: int) -> Optional[Dict[str, Any]]:
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM help_requests WHERE id = ?", (question_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    @staticmethod
    def update_answer(question_id: int, answer: str):
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE help_requests SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (answer, question_id)
                )
                conn.commit()

    @staticmethod
    def get_pending_questions():
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM help_requests WHERE status = 'pending' ORDER BY id")
                return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def mark_unresolved(question_id: int):
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE help_requests SET status = 'unresolved', answered_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (question_id,)
                )
                conn.commit()

    @staticmethod
    def get_all_history():
        with _lock:
            with HumanQueueDB._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM help_requests ORDER BY answered_at DESC")
                return [dict(row) for row in cur.fetchall()]

# === EXPORT INSTANCE ===
human_queue_db = HumanQueueDB()