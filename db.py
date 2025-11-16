# db.py
import sqlite3
from typing import Optional


class Database:
    def __init__(self, db_path: str = "nco_data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nco_info (
                    user_id INTEGER PRIMARY KEY,
                    nco_name TEXT,
                    activities TEXT,
                    audience TEXT,
                    website TEXT
                )
            """)

    def save_nco_info(self, user_id: int, nco_name: str, activities: str, audience: str, website: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO nco_info (user_id, nco_name, activities, audience, website)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    nco_name=excluded.nco_name,
                    activities=excluded.activities,
                    audience=excluded.audience,
                    website=excluded.website
            """, (user_id, nco_name, activities, audience, website))

    def get_nco_info(self, user_id: int) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT nco_name, activities, audience, website FROM nco_info WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'name': row[0] or '',
                    'activities': row[1] or '',
                    'audience': row[2] or '',
                    'website': row[3] or ''
                }
        return None