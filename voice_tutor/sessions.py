"""Private, local-only SQLite sessions. No recordings are persisted."""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def clean_session_title(value: object) -> str:
    """Short one-line AI-created title; no user-message fallback."""
    if not isinstance(value, str):
        return ""
    title = " ".join(value.strip().strip("\"'「」『』`。，、。！!：:").split())
    if not 2 <= len(title) <= 36 or "\n" in title:
        return ""
    return title[:28]


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audio_dir = self.path.parent / "audio_cache"
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                user_text TEXT NOT NULL, reply_ja TEXT NOT NULL,
                correction_ja TEXT NOT NULL, feedback_zh TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
            # Non-destructive migration: existing messages, cached speech and titles stay intact.
            columns = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
            if "is_pinned" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
            if "title_status" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN title_status TEXT NOT NULL DEFAULT 'pending'")
                # Existing sessions named by the user's first message need AI titles.
                # Preserve titles that already differ substantively from that message.
                for row in db.execute("""SELECT s.id,s.title,
                    (SELECT m.user_text FROM messages m WHERE m.session_id=s.id ORDER BY m.id LIMIT 1) AS first_text
                    FROM sessions s"""):
                    title=(row["title"] or "").strip()
                    first=(row["first_text"] or "").strip()
                    looks_copied=bool(first and (first.startswith(title) or title.startswith(first[:min(len(first),16)])))
                    if title not in ("", "新对话") and not looks_copied:
                        db.execute("UPDATE sessions SET title_status='ai' WHERE id=?",(row["id"],))
            if "title_attempts" not in columns:
                db.execute("ALTER TABLE sessions ADD COLUMN title_attempts INTEGER NOT NULL DEFAULT 0")
            message_columns = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
            if "corrects_message_id" not in message_columns:
                db.execute("ALTER TABLE messages ADD COLUMN corrects_message_id INTEGER")
            # A killed worker must not leave titles permanently unprocessed.
            db.execute("UPDATE sessions SET title_status='pending' WHERE title_status='processing'")

    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def list_sessions(self, limit: int = 100):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT id,title,created_at,updated_at,is_pinned,title_status FROM sessions ORDER BY is_pinned DESC,updated_at DESC LIMIT ?", (limit,)
            ).fetchall()]

    def get(self, sid: str):
        with self.connect() as db:
            row = db.execute("SELECT id,title,created_at,updated_at,is_pinned,title_status FROM sessions WHERE id=?", (sid,)).fetchone()
            if row is None:
                return None
            messages = [dict(x) for x in db.execute(
                "SELECT id,user_text,reply_ja,correction_ja,feedback_zh,created_at,corrects_message_id FROM messages WHERE session_id=? ORDER BY id", (sid,)
            ).fetchall()]
            for message in messages:
                # Generated speech is stored locally; microphone recordings are never stored.
                cached = self.audio_path(message["id"], "azusa_e36")
                message["audio_url"] = (
                    f"/api/audio/{sid}/{message['id']}?voice_id=azusa_e36"
                    if cached.is_file() else None
                )
            return {**dict(row), "messages": messages}

    def audio_path(self, message_id: int, voice_id: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", voice_id):
            raise ValueError("Invalid voice ID")
        if int(message_id) < 1:
            raise ValueError("Invalid message ID")
        return self.audio_dir / f"{int(message_id)}_{voice_id}.wav"

    def message_in_session(self, sid: str, message_id: int):
        with self.connect() as db:
            row = db.execute(
                "SELECT id,session_id,user_text,reply_ja FROM messages WHERE id=? AND session_id=?",
                (message_id, sid)
            ).fetchone()
            return dict(row) if row else None

    def save_audio(self, sid: str, message_id: int, voice_id: str, data: bytes) -> Path:
        if self.message_in_session(sid, message_id) is None:
            raise KeyError("Message not found")
        path = self.audio_path(message_id, voice_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.stem + "_" + uuid4().hex + ".tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def add_turn(self, sid: str | None, user_text: str, result: dict, *, return_id: bool = False, corrects_message_id: int | None = None):
        sid = sid or str(uuid4())
        now = stamp()
        with self.connect() as db:
            row = db.execute("SELECT id FROM sessions WHERE id=?", (sid,)).fetchone()
            if row is None:
                title=clean_session_title(result.get("session_title"))
                db.execute("INSERT INTO sessions(id,title,created_at,updated_at,title_status) VALUES(?,?,?,?,?)",
                           (sid, title or "新对话", now, now, 'ai' if title else 'pending'))
            else:
                db.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, sid))
                title = clean_session_title(result.get("session_title"))
                if title:
                    db.execute("UPDATE sessions SET title=?,title_status='ai' WHERE id=? AND title_status!='ai'", (title, sid))
            cursor = db.execute("""INSERT INTO messages(session_id,user_text,reply_ja,correction_ja,feedback_zh,created_at,corrects_message_id)
                         VALUES(?,?,?,?,?,?,?)""", (
                sid, user_text, result["reply_ja"], result["correction_ja"], result["feedback_zh"], now, corrects_message_id
            ))
        return (sid, cursor.lastrowid) if return_id else sid

    def set_pinned(self, sid: str, pinned: bool) -> bool:
        with self.connect() as db:
            cursor = db.execute("UPDATE sessions SET is_pinned=? WHERE id=?", (int(pinned), sid))
            return bool(cursor.rowcount)

    def set_title(self, sid: str, title: str) -> str | None:
        title = clean_session_title(title)
        if not title:
            raise ValueError("AI did not produce a valid title")
        with self.connect() as db:
            cursor = db.execute("UPDATE sessions SET title=?,title_status='ai' WHERE id=?", (title, sid))
            return title if cursor.rowcount else None

    def claim_untitled(self):
        """Reserve one legacy or untitled conversation for bounded background AI retitling."""
        with self.connect() as db:
            row=db.execute("""SELECT s.id FROM sessions s
                WHERE s.title_status='pending' AND s.title_attempts < 2
                AND EXISTS (SELECT 1 FROM messages m WHERE m.session_id=s.id)
                ORDER BY s.updated_at DESC LIMIT 1""").fetchone()
            if not row:
                return None
            sid=row['id']
            db.execute("UPDATE sessions SET title_status='processing' WHERE id=?", (sid,))
            return sid

    def release_title_attempt(self,sid):
        with self.connect() as db:
            db.execute("""UPDATE sessions SET title_status='pending',title_attempts=title_attempts+1
                          WHERE id=? AND title_status='processing'""",(sid,))

    def history(self, sid: str | None, last_n: int = 12):
        if not sid:
            return []
        session = self.get(sid)
        if not session:
            return []
        out = []
        for record in session["messages"][-last_n:]:
            text = record["user_text"]
            if record.get("corrects_message_id"):
                text = ("[This utterance corrects an earlier user message and supersedes "
                        "that transcript. Continue the same conversation.]\n" + text)
            out.extend([{"role": "user", "content": text},
                        {"role": "assistant", "content": record["reply_ja"]}])
        return out

    def delete(self, sid: str) -> bool:
        with self.connect() as db:
            ids = [int(r[0]) for r in db.execute(
                "SELECT id FROM messages WHERE session_id=?", (sid,)
            ).fetchall()]
            cursor = db.execute("DELETE FROM sessions WHERE id=?", (sid,))
            deleted = bool(cursor.rowcount)
        if deleted and self.audio_dir.is_dir():
            for message_id in ids:
                for cached in self.audio_dir.glob(f"{message_id}_*.wav"):
                    cached.unlink(missing_ok=True)
        return deleted

    def export_json(self, sid: str):
        data = self.get(sid)
        if data is None:
            raise KeyError(sid)
        return json.dumps(data, ensure_ascii=False, indent=2)
