import sqlite3
db_name = 'SpeechKit.db'
class SpeechKit:
    def __init__(self, db_name=db_name):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_database()
    def create_database(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS symbols (
                                chat_id INTEGER PRIMARY KEY,
                                token_count INTEGER DEFAULT 10000
                            )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS blocks (
                                        chat_id INTEGER PRIMARY KEY,
                                        blocks_count INTEGER DEFAULT 120
                                    )''')
        self.conn.commit()
    def add_user(self, chat_id, token_count=10000):
        self.cursor.execute("INSERT OR IGNORE INTO symbols (chat_id, token_count) VALUES (?, ?)", (chat_id, token_count))
        self.cursor.execute("INSERT OR IGNORE INTO blocks (chat_id, blocks_count) VALUES (?, ?)",(chat_id, 120))
        self.conn.commit()
    def get_token_count(self, chat_id):
        self.cursor.execute("SELECT token_count FROM symbols WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        elif result <= 100:
            return 0
        else:
            return 0
    def get_blocks_vount(self, chat_id):
        self.cursor.execute("SELECT blocks_count FROM blocks WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        elif result <= 3:
            return 0
        else:
            return 0
    def update_token_count(self, chat_id, new_count):
        self.cursor.execute("UPDATE symbols SET token_count = ? WHERE chat_id = ?", (new_count, chat_id))
        self.conn.commit()
    def update_blocks_count(self, chat_id, new_count):
        self.cursor.execute("UPDATE blocks SET blocks_count =? WHERE chat_id =?", (new_count, chat_id))
        self.conn.commit()
    def close(self):
        self.conn.close()