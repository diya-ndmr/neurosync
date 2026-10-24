from __future__ import annotations

import argparse

from lms.database import ensure_lms_db
from lms.generator import generate_mock_lms


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the 500-student mock LMS dataset.")
    parser.add_argument("--db-path", default=None, help="Path to the SQLite database file (defaults to the application's Mock LMS database)")
    parser.add_argument("--recreate", action="store_true", help="Delete and regenerate the dataset")
    args = parser.parse_args()

    summary = generate_mock_lms(db_path=args.db_path, recreate=args.recreate)
    print("Mock LMS dataset generated successfully.")
    print(f"Database path: {ensure_lms_db(args.db_path)}")
    print(f"Student count: {summary['student_count']}")
    print(f"Programme count: {summary['programme_count']}")
    print(f"Module count: {summary['module_count']}")
    print(f"Assessment count: {summary['assessment_count']}")
    print(f"Quiz count: {summary['quiz_count']}")
    print(f"LMS activity count: {summary['lms_activity_count']}")
    print(f"Resource activity count: {summary['resource_activity_count']}")


if __name__ == "__main__":
    main()
