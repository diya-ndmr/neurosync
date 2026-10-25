"""Seed-script regression tests.

Two defects are pinned here:

1. The old ``if db.query(User).first(): print("already seeded"); exit(0)`` guard meant
   a partially seeded database could never be repaired — the shipped demo database
   was missing all five attendance rows for the documented student account
   (``s-1001``) and every re-run silently skipped the fix.
2. Attendance percentages were derived from the built-in ``hash()``, which is salted
   per interpreter, so the same demo database produced different dashboard numbers
   on every run.

Both tests execute the real script in a subprocess against a throwaway SQLite file.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TABLES = [
    "users",
    "students",
    "modules",
    "attendance",
    "assessments",
    "study_sessions",
    "mood_checkins",
    "risk_predictions",
    "recommendations",
]
DEMO_STUDENTS = ["s-1001", "s-2002", "s-2003", "s-2004", "s-2005", "s-2006"]


def run_seed(db_path: Path, hash_seed: str = "0") -> str:
    env = {
        **os.environ,
        # Environment variables take priority over backend/.env, so the developer's
        # own database is never touched by these tests.
        "DATABASE_URL": f"sqlite:///{db_path}",
        "ENVIRONMENT": "test",
        "PYTHONHASHSEED": hash_seed,
    }
    result = subprocess.run(
        [sys.executable, "seed.py"], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def query(db_path: Path, statement: str):
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(statement).fetchall()
        connection.commit()
        return rows
    finally:
        connection.close()


def row_counts(db_path: Path) -> dict:
    return {table: query(db_path, f"select count(*) from {table}")[0][0] for table in TABLES}


def attendance_rows(db_path: Path):
    return query(db_path, "select student_id, module_id, attendance_percentage from attendance order by student_id, module_id")


def test_seed_is_idempotent_and_repairs_missing_rows(tmp_path):
    db_path = tmp_path / "seed.db"

    first_run = run_seed(db_path)
    assert "Created:" in first_run
    expected = row_counts(db_path)
    assert expected["users"] == 9
    assert expected["students"] == 6
    assert expected["attendance"] == len(DEMO_STUDENTS) * 5

    # Emulate the partially seeded database: the documented student lost its rows.
    query(db_path, "delete from attendance where student_id = 's-1001'")
    assert row_counts(db_path)["attendance"] == (len(DEMO_STUDENTS) - 1) * 5

    repaired = run_seed(db_path)
    assert "Attendance=5" in repaired, repaired
    assert row_counts(db_path) == expected

    third_run = run_seed(db_path)
    assert "already complete" in third_run, third_run
    assert row_counts(db_path) == expected


def test_attendance_percentages_are_deterministic_across_processes(tmp_path):
    first = tmp_path / "a.db"
    second = tmp_path / "b.db"

    run_seed(first, hash_seed="0")
    run_seed(second, hash_seed="12345")

    rows = attendance_rows(first)
    assert len(rows) == len(DEMO_STUDENTS) * 5
    # Identical numbers under two different hash seeds: the values can no longer
    # come from the salted built-in hash().
    assert rows == attendance_rows(second)
    assert all(40 <= percentage <= 100 for _, _, percentage in rows)
    assert {student for student, _, _ in rows} == set(DEMO_STUDENTS)


def test_seed_refuses_to_create_public_demo_accounts_in_production(tmp_path):
    db_path = tmp_path / "production.db"
    env = {
        **os.environ,
        "DATABASE_URL": "postgresql://app-db.example.edu/neurosync",
        "ENVIRONMENT": "production",
        "MOCK_SSO_ENABLED": "false",
        "ALLOW_DEMO_TOKENS": "false",
        "SECRET_KEY": "production-test-key-with-enough-unique-characters-123",
        "CORS_ORIGINS": '["https://neurosync.example"]',
        "SUPABASE_URL": "https://project-ref.supabase.co",
        "SUPABASE_ANON_KEY": "test-supabase-anon-key",
        "FRONTEND_URL": "https://neurosync.example",
    }
    result = subprocess.run(
        [sys.executable, "seed.py"], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "public demo passwords in production" in result.stderr
