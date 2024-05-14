import sqlite3
import logging
class Tokens:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                chat_id INTEGER PRIMARY KEY,
                tokens INTEGER
            )
        """)
        self.conn.commit()
    def create_user_profile(self, chat_id):
        self.cursor.execute("INSERT OR IGNORE INTO sessions (chat_id , tokens) VALUES ( ?, ?)", (chat_id, 4000))
        self.conn.commit()
    def deduct_tokens(self, chat_id, tokens_count):
        logging.info(f"Отнимаем {tokens_count} токенов у пользователя {chat_id}")
        self.cursor.execute("UPDATE sessions SET tokens = tokens - ? WHERE chat_id = ?", (tokens_count, chat_id))
        self.conn.commit()
    def get_tokens(self, chat_id):
        self.cursor.execute("SELECT tokens FROM sessions WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        elif result <= 50:
            return 0
        else:
            return 0

    def close_connection(self):
        self.conn.close()