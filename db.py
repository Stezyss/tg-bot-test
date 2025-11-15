# db.py
import sqlite3
from typing import Optional, Dict


class Database:
    def __init__(self, db_path: str = 'bot.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_nco_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                nco_name TEXT,
                activities TEXT,
                audience TEXT,
                website TEXT
            )
        ''')
        self.conn.commit()

    def save_nco_info(
        self,
        user_id: int,
        nco_name: str = None,
        activities: str = None,
        audience: str = None,
        website: str = None
    ):
        self.conn.execute(
            '''
            INSERT OR REPLACE INTO user_nco_info 
            (user_id, nco_name, activities, audience, website)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (user_id, nco_name, activities, audience, website)
        )
        self.conn.commit()

    def get_nco_info(self, user_id: int) -> Optional[Dict]:
        cursor = self.conn.execute(
            'SELECT nco_name, activities, audience, website FROM user_nco_info WHERE user_id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'name': row[0] or '',
                'activities': row[1] or '',
                'audience': row[2] or '',
                'website': row[3] or ''
            }
        return None

    def close(self):
        self.conn.close()