"""SQLite persistence layer for the AI Resume Screener."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploaded_resumes"
DB_PATH = DATA_DIR / "resume_screener.db"

# Module-level flag to avoid re-running schema migration on every DB call.
_storage_initialized: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_storage() -> None:
    """Create application storage and the SQLite schema (idempotent; runs once per process)."""
    global _storage_initialized
    if _storage_initialized:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        UPLOAD_DIR.chmod(0o700)
    except OSError:
        pass  # Windows may not support Unix permissions; silently continue

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                target_role TEXT NOT NULL,
                years_exp REAL NOT NULL DEFAULT 0,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                word_count INTEGER NOT NULL DEFAULT 0,
                parse_status TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'candidate_portal',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                job_description TEXT NOT NULL,
                match_score INTEGER NOT NULL CHECK(match_score BETWEEN 0 AND 100),
                recommendation TEXT NOT NULL,
                matching_skills TEXT NOT NULL DEFAULT '[]',
                missing_skills TEXT NOT NULL DEFAULT '[]',
                justification TEXT NOT NULL,
                estimated_experience_years REAL,
                status TEXT NOT NULL,
                screened_at TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_created ON candidates(created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_screenings_candidate ON screenings(candidate_id, screened_at DESC)")
        conn.commit()

    _storage_initialized = True


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with WAL mode, foreign keys enabled, and proper rollback on error."""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _candidate_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def save_resume(
    *,
    name: str,
    email: str,
    target_role: str,
    years_exp: float,
    original_filename: str,
    file_bytes: bytes,
    page_count: int,
    word_count: int,
    parse_status: str,
    source: str = "candidate_portal",
) -> dict[str, Any]:
    """Persist a PDF with an opaque filename and upsert candidate metadata by email."""
    ensure_storage()
    normalized_email = email.strip().lower()
    # Sanitize the original filename — keep only the basename to prevent path traversal
    safe_original_filename = Path(original_filename).name
    safe_id = str(uuid4())
    stored_filename = f"{safe_id}.pdf"
    destination = UPLOAD_DIR / stored_filename
    temp_path = UPLOAD_DIR / f".{safe_id}.tmp"

    # Write atomically so an interrupted upload does not leave a partial PDF registered in the DB.
    temp_path.write_bytes(file_bytes)
    try:
        temp_path.replace(destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass

        now = _utc_now()
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT id, stored_filename, file_path FROM candidates WHERE email = ?",
                (normalized_email,),
            ).fetchone()

            if existing:
                candidate_id = existing["id"]
                old_stored = existing["stored_filename"]
                old_path = UPLOAD_DIR / old_stored
                conn.execute(
                    """
                    UPDATE candidates
                    SET name=?, target_role=?, years_exp=?, original_filename=?,
                        stored_filename=?, file_path=?, file_size_bytes=?, page_count=?,
                        word_count=?, parse_status=?, source=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        name.strip(), target_role.strip(), float(years_exp), safe_original_filename,
                        stored_filename, str(destination.relative_to(BASE_DIR)), len(file_bytes),
                        int(page_count), int(word_count), parse_status, source, now, candidate_id,
                    ),
                )
                # Remove the previous physical file only after the DB update succeeds.
                if old_path != destination and old_path.exists() and old_path.parent == UPLOAD_DIR:
                    old_path.unlink(missing_ok=True)
            else:
                candidate_id = safe_id
                conn.execute(
                    """
                    INSERT INTO candidates
                    (id, name, email, target_role, years_exp, original_filename, stored_filename,
                     file_path, file_size_bytes, page_count, word_count, parse_status, source,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate_id, name.strip(), normalized_email, target_role.strip(), float(years_exp),
                        safe_original_filename, stored_filename, str(destination.relative_to(BASE_DIR)),
                        len(file_bytes), int(page_count), int(word_count), parse_status, source, now, now,
                    ),
                )

            # A replaced resume should not retain stale AI results.
            conn.execute("DELETE FROM screenings WHERE candidate_id = ?", (candidate_id,))

        return get_candidate(candidate_id)  # type: ignore[return-value]
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        temp_path.unlink(missing_ok=True)


def add_screening(
    *,
    candidate_id: str,
    job_description: str,
    match_score: int,
    recommendation: str,
    matching_skills: list[str],
    missing_skills: list[str],
    justification: str,
    estimated_experience_years: Optional[float],
    status: str,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO screenings
            (candidate_id, job_description, match_score, recommendation, matching_skills,
             missing_skills, justification, estimated_experience_years, status, screened_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id, job_description.strip(), int(match_score), recommendation,
                json.dumps(matching_skills), json.dumps(missing_skills), justification,
                estimated_experience_years, status, _utc_now(),
            ),
        )
        return int(cur.lastrowid)


def get_candidate(candidate_id: str) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _candidate_row(row) if row else None


def get_candidates() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()
        return [_candidate_row(row) for row in rows]


def get_screening_results() -> list[dict[str, Any]]:
    """Return the latest screening for every candidate, if one exists."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*, s.match_score, s.recommendation, s.matching_skills, s.missing_skills,
                   s.justification, s.estimated_experience_years, s.status AS screening_status,
                   s.screened_at, s.job_description
            FROM candidates c
            LEFT JOIN screenings s ON s.id = (
                SELECT s2.id FROM screenings s2
                WHERE s2.candidate_id = c.id
                ORDER BY s2.screened_at DESC, s2.id DESC
                LIMIT 1
            )
            ORDER BY COALESCE(s.match_score, -1) DESC, c.created_at DESC
            """
        ).fetchall()

        results = []
        for row in rows:
            item = _candidate_row(row)
            item["matching_skills"] = json.loads(item.pop("matching_skills") or "[]")
            item["missing_skills"] = json.loads(item.pop("missing_skills") or "[]")
            results.append(item)
        return results


def get_stats() -> dict[str, Any]:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        screened = conn.execute("SELECT COUNT(DISTINCT candidate_id) FROM screenings").fetchone()[0]
        top = conn.execute("SELECT MAX(match_score) FROM screenings").fetchone()[0]
        avg = conn.execute("SELECT AVG(match_score) FROM screenings").fetchone()[0]
        return {
            "total": int(total),
            "screened": int(screened),
            "top_score": int(top) if top is not None else None,
            "average_score": round(float(avg), 1) if avg is not None else None,
        }


def delete_candidate(candidate_id: str) -> bool:
    """Delete a candidate and their stored resume. Intended for authenticated recruiter actions."""
    with get_connection() as conn:
        row = conn.execute("SELECT stored_filename FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not row:
            return False
        stored_filename = row["stored_filename"]
        # Verify the file is within the expected upload directory before deletion.
        file_path = UPLOAD_DIR / stored_filename
        deleted = conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,)).rowcount > 0
        if deleted and file_path.parent == UPLOAD_DIR and file_path.exists():
            file_path.unlink(missing_ok=True)
        return deleted


def delete_all_candidates() -> bool:
    """Clears all candidates and their stored resumes to reset the dashboard."""
    with get_connection() as conn:
        rows = conn.execute("SELECT stored_filename FROM candidates").fetchall()

        # Delete from tables (cascade handles screenings via FK)
        conn.execute("DELETE FROM screenings")
        conn.execute("DELETE FROM candidates")

        # Delete physical files — only those inside UPLOAD_DIR
        for row in rows:
            stored_filename = row["stored_filename"]
            file_path = UPLOAD_DIR / stored_filename
            if file_path.parent == UPLOAD_DIR:
                file_path.unlink(missing_ok=True)

    return True