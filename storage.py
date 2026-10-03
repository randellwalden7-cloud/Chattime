import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

class Storage:
    def __init__(self, path='data/chattime.db'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL REFERENCES users(username), engine TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
                    created TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS feedback (
                    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                    value INTEGER NOT NULL CHECK (value IN (0,1)));
            ''')
        os.chmod(path, 0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @staticmethod
    def digest(password, salt):
        return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                              n=16384, r=8, p=1).hex()

    def register(self, username, password):
        username = username.strip().lower()
        if not 3 <= len(username) <= 80 or not 12 <= len(password) <= 256:
            raise ValueError('Use a username of 3–80 characters and a password of 12–256 characters.')
        salt = secrets.token_hex(16)
        with self.connect() as db:
            db.execute('INSERT INTO users VALUES (?,?,?)',
                       (username, salt, self.digest(password, salt)))
        return username

    def verify(self, username, password):
        if len(password) > 256:
            return False
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        salt = row['salt'] if row else '00' * 16
        actual = self.digest(password, salt)
        return bool(row and hmac.compare_digest(actual, row['digest']))

    def load(self, username, engine):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM messages WHERE username=? AND engine=? ORDER BY id', (username, engine))]

    def save(self, username, engine, role, content, usage=None):
        usage = usage or {}
        with self.connect() as db:
            return db.execute('''INSERT INTO messages
                (username,engine,role,content,input_tokens,output_tokens) VALUES (?,?,?,?,?,?)''',
                (username, engine, role, content, usage.get('input_tokens', 0),
                 usage.get('output_tokens', 0))).lastrowid

    def clear(self, username, engine):
        with self.connect() as db:
            db.execute('DELETE FROM messages WHERE username=? AND engine=?', (username, engine))

    def feedback(self, username, message_id, value):
        with self.connect() as db:
            row = db.execute('SELECT id FROM messages WHERE id=? AND username=? AND role=?',
                             (message_id, username, 'assistant')).fetchone()
            if not row:
                raise ValueError('Message not found.')
            db.execute('INSERT INTO feedback VALUES (?,?) ON CONFLICT(message_id) DO UPDATE SET value=excluded.value',
                       (message_id, value))
