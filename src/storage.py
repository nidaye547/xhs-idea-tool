import csv
import re
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
from pathlib import Path

from .config import DATABASE_PATH, OUTPUT_DIR


def get_schema() -> str:
    return """
    CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_crawled_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword_id INTEGER REFERENCES keywords(id),
        note_id TEXT UNIQUE NOT NULL,
        title TEXT,
        content TEXT,
        author TEXT,
        published_at TIMESTAMP,
        comment_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_crawled_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id TEXT REFERENCES notes(note_id),
        comment_id TEXT UNIQUE NOT NULL,
        user TEXT,
        content TEXT,
        like_count INTEGER DEFAULT 0,
        created_at TIMESTAMP,
        is_ai_analyzed BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS ai_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id TEXT REFERENCES notes(note_id),
        aggregated_view TEXT,
        feasibility_score INTEGER,
        reasoning TEXT,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_comments_note_id ON comments(note_id);
    CREATE INDEX IF NOT EXISTS idx_notes_keyword_id ON notes(keyword_id);
    """


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(get_schema())
        conn.commit()
        yield conn
    finally:
        conn.close()


class Storage:
    def __init__(self):
        with get_connection() as conn:
            conn.executescript(get_schema())
            conn.commit()

    def add_keyword(self, keyword: str) -> int:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)",
                (keyword,)
            )
            conn.commit()
            # Get the ID whether newly inserted or already existed
            row = conn.execute(
                "SELECT id FROM keywords WHERE keyword = ?",
                (keyword,)
            ).fetchone()
            return row["id"] if row else 0

    def get_keyword_id(self, keyword: str) -> Optional[int]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM keywords WHERE keyword = ?",
                (keyword,)
            ).fetchone()
            return row["id"] if row else None

    def update_keyword_crawled(self, keyword: str):
        with get_connection() as conn:
            conn.execute(
                "UPDATE keywords SET last_crawled_at = ? WHERE keyword = ?",
                (datetime.now(), keyword)
            )
            conn.commit()

    def add_note(self, keyword_id: int, note_id: str, title: str, content: str,
                 author: str, published_at: str, comment_count: int) -> bool:
        with get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO notes (keyword_id, note_id, title, content, author,
                                      published_at, comment_count, last_crawled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (keyword_id, note_id, title, content, author, published_at,
                      comment_count, datetime.now()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Note already exists, update
                conn.execute("""
                    UPDATE notes SET title=?, content=?, author=?, published_at=?,
                                    comment_count=?, last_crawled_at=?
                    WHERE note_id=?
                """, (title, content, author, published_at, comment_count,
                      datetime.now(), note_id))
                conn.commit()
                return False

    def add_comments(self, note_id: str, comments: list) -> int:
        """Add comments, returns number of new comments added."""
        with get_connection() as conn:
            count = 0
            for c in comments:
                try:
                    conn.execute("""
                        INSERT INTO comments (note_id, comment_id, user, content,
                                             like_count, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (note_id, c["id"], c.get("user", ""), c.get("content", ""),
                          c.get("like_count", 0), c.get("created_at", "")))
                    count += 1
                except sqlite3.IntegrityError:
                    pass  # Skip duplicate
            conn.commit()
            return count

    def get_note_ids_for_keyword(self, keyword_id: int) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT note_id FROM notes WHERE keyword_id = ?",
                (keyword_id,)
            ).fetchall()
            return [r["note_id"] for r in rows]

    def get_comments_for_note(self, note_id: str) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE note_id = ? ORDER BY like_count DESC",
                (note_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_unanalyzed_comments(self, note_id: str) -> list:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE note_id = ? AND is_ai_analyzed = 0",
                (note_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_comments_analyzed(self, comment_ids: list):
        if not comment_ids:
            return
        placeholders = ",".join("?" * len(comment_ids))
        with get_connection() as conn:
            conn.execute(
                f"UPDATE comments SET is_ai_analyzed = 1 WHERE comment_id IN ({placeholders})",
                comment_ids
            )
            conn.commit()

    def save_ai_result(self, note_id: str, aggregated_view: str,
                       feasibility_score: int, reasoning: str):
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO ai_results (note_id, aggregated_view, feasibility_score, reasoning)
                VALUES (?, ?, ?, ?)
            """, (note_id, aggregated_view, feasibility_score, reasoning))
            conn.commit()

    def get_ai_results(self, note_id: str = None, min_score: int = 3) -> list:
        with get_connection() as conn:
            if note_id:
                rows = conn.execute("""
                    SELECT * FROM ai_results
                    WHERE note_id = ? AND feasibility_score >= ?
                    ORDER BY feasibility_score DESC
                """, (note_id, min_score)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM ai_results
                    WHERE feasibility_score >= ?
                    ORDER BY feasibility_score DESC
                """, (min_score,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_keywords(self) -> list:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM keywords").fetchall()
            return [dict(r) for r in rows]

    def export_comments_to_csv(self, keyword: str, cleaned_comments: list) -> str:
        """Export cleaned comments to CSV file by keyword."""
        OUTPUT_DIR.mkdir(exist_ok=True)
        # Sanitize keyword for filename
        safe_keyword = re.sub(r'[^\w\s-]', '', keyword).strip()
        safe_keyword = re.sub(r'\s+', '_', safe_keyword)
        filename = f"{safe_keyword}_comments.csv"
        filepath = OUTPUT_DIR / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['note_id', 'note_title', 'user', 'content', 'like_count', 'cleaned_view', 'feasibility_score', 'reasoning'])
            for comment in cleaned_comments:
                writer.writerow([
                    comment.get('note_id', ''),
                    comment.get('note_title', ''),
                    comment.get('user', ''),
                    comment.get('content', ''),
                    comment.get('like_count', 0),
                    comment.get('cleaned_view', ''),
                    comment.get('feasibility_score', ''),
                    comment.get('reasoning', '')
                ])

        print(f"Exported {len(cleaned_comments)} comments to {filepath}")
        return str(filepath)

    def get_comments_with_note_info(self, keyword_id: int) -> list:
        """Get all comments with note info for a keyword."""
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT c.*, n.title as note_title
                FROM comments c
                JOIN notes n ON c.note_id = n.note_id
                WHERE n.keyword_id = ?
                ORDER BY c.like_count DESC
            """, (keyword_id,)).fetchall()
            return [dict(r) for r in rows]
