import uuid
import zlib
from collections import Counter
from datetime import datetime, timedelta, timezone, date

from app.database.connection import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.student import StudentProfile
from app.models.module import Module
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.study_session import StudySession
from app.models.mood_checkin import MoodCheckin
from app.models.risk_prediction import RiskPrediction, RiskLevel
from app.models.recommendation import Recommendation
from app.services.authentication_service import hash_password
from app.config.settings import settings

if settings.environment == "production":
    raise SystemExit("Refusing to create accounts with public demo passwords in production.")

Base.metadata.create_all(bind=engine)
db = SessionLocal()

created: Counter = Counter()


def row_id(kind: str, *parts: str) -> str:
    """Stable identifier so repeat runs address the same row."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "neurosync/seed/" + kind + "/" + "/".join(parts)))


def attendance_percentage(student_id: str, module_index: int) -> float:
    """Deterministic 40-100 percentage (``hash()`` is salted per interpreter)."""
    digest = zlib.crc32(f"{student_id}:{module_index}".encode())
    return float(max(40, min(100, 85 + (module_index * 2) - (digest % 30))))


def upsert(model, natural_key, **fields):
    """Insert only when the natural key is absent; return True when inserted."""
    existing = db.query(model).filter_by(**natural_key).first()
    if existing is not None:
        return False
    db.add(model(**fields))
    created[model.__name__] += 1
    return True


try:
    now = datetime.now(timezone.utc)

    # ── Users ──
    users = [
        dict(id="u-sarah", email="sarah@university.edu", name="Sarah Johnson", role=UserRole.student),
        dict(id="u-liam", email="liam@university.edu", name="Liam Patel", role=UserRole.student),
        dict(id="u-aisha", email="aisha@university.edu", name="Aisha Mohammed", role=UserRole.student),
        dict(id="u-daniel", email="daniel@university.edu", name="Daniel Osei", role=UserRole.student),
        dict(id="u-emma", email="emma@university.edu", name="Emma Botha", role=UserRole.student),
        dict(id="u-noah", email="noah@university.edu", name="Noah van der Berg", role=UserRole.student),
        dict(id="u-lecturer", email="lecturer@university.edu", name="Dr. Mark Thompson", role=UserRole.lecturer),
        dict(id="u-advisor", email="advisor@university.edu", name="Amelia Richards", role=UserRole.advisor),
        dict(id="u-admin", email="admin@university.edu", name="Prof. James Carter", role=UserRole.admin),
    ]
    for user in users:
        # Hash lazily: bcrypt is deliberately slow and re-hashing existing demo
        # accounts on every run would waste seconds for no benefit.
        if db.query(User).filter(User.email == user["email"]).first() is None:
            db.add(User(password_hash=hash_password("demo1234"), **user))
            created["User"] += 1
    db.flush()

    # ── Student profiles ──
    students = [
        dict(id="s-1001", user_id="u-sarah", student_number="NS2024001", first_name="Sarah", surname="Johnson", programme="Bachelor of Information Technology", year_level=2),
        dict(id="s-2002", user_id="u-liam", student_number="NS2024022", first_name="Liam", surname="Patel", programme="Bachelor of Information Technology", year_level=2),
        dict(id="s-2003", user_id="u-aisha", student_number="NS2024034", first_name="Aisha", surname="Mohammed", programme="Bachelor of Computer Science", year_level=3),
        dict(id="s-2004", user_id="u-daniel", student_number="NS2024051", first_name="Daniel", surname="Osei", programme="Bachelor of Information Technology", year_level=2),
        dict(id="s-2005", user_id="u-emma", student_number="NS2024067", first_name="Emma", surname="Botha", programme="Bachelor of Computing", year_level=1),
        dict(id="s-2006", user_id="u-noah", student_number="NS2024090", first_name="Noah", surname="van der Berg", programme="Bachelor of Computer Science", year_level=2),
    ]
    for student in students:
        upsert(StudentProfile, {"student_number": student["student_number"]}, **student)
    db.flush()

    # ── Modules ──
    modules = [
        dict(id="m-db", module_code="DB201", module_name="Database Systems", faculty="Computing"),
        dict(id="m-wd", module_code="WD202", module_name="Web Development", faculty="Computing"),
        dict(id="m-ds", module_code="DS203", module_name="Data Structures", faculty="Computing"),
        dict(id="m-nt", module_code="NT204", module_name="Networking", faculty="Computing"),
        dict(id="m-se", module_code="SE205", module_name="Software Engineering", faculty="Computing"),
    ]
    for module in modules:
        upsert(Module, {"module_code": module["module_code"]}, **module)
    db.flush()

    # ── Assessments ──
    assessments = [
        ("s-1001", "m-db", "Exam", 84, date(2025, 8, 18)),
        ("s-1001", "m-wd", "Coursework", 76, date(2025, 8, 12)),
        ("s-1001", "m-ds", "Exam", 68, date(2025, 8, 15)),
        ("s-1001", "m-nt", "Practical", 86, date(2025, 8, 10)),
        ("s-1001", "m-se", "Coursework", 77, date(2025, 8, 8)),
        ("s-1001", "m-db", "Coursework", 81, date(2025, 7, 25)),
        ("s-1001", "m-ds", "Quiz", 58, date(2025, 7, 20)),
        ("s-2002", "m-ds", "Exam", 54, date(2025, 8, 15)),
        ("s-2002", "m-db", "Coursework", 48, date(2025, 8, 10)),
        ("s-2003", "m-wd", "Exam", 88, date(2025, 8, 15)),
        ("s-2004", "m-nt", "Practical", 63, date(2025, 8, 12)),
        ("s-2005", "m-se", "Coursework", 81, date(2025, 8, 14)),
        ("s-2006", "m-ds", "Exam", 48, date(2025, 8, 15)),
    ]
    for student_id, module_id, assessment_type, mark, assessed_on in assessments:
        upsert(
            Assessment,
            {
                "student_id": student_id,
                "module_id": module_id,
                "assessment_type": assessment_type,
                "mark": float(mark),
                "assessment_date": assessed_on,
            },
            id=row_id("assessment", student_id, module_id, assessment_type, str(assessed_on)),
            student_id=student_id,
            module_id=module_id,
            assessment_type=assessment_type,
            mark=float(mark),
            assessment_date=assessed_on,
        )
    db.flush()

    # ── Attendance ──
    # Every demo student attends every module, including the documented student
    # account (s-1001). Percentages are deterministic so re-seeding a fresh
    # database reproduces the same dashboard numbers.
    for student_id in ["s-1001", "s-2002", "s-2003", "s-2004", "s-2005", "s-2006"]:
        for index, module_id in enumerate(["m-db", "m-wd", "m-ds", "m-nt", "m-se"]):
            percentage = attendance_percentage(student_id, index)
            upsert(
                Attendance,
                {"student_id": student_id, "module_id": module_id},
                id=row_id("attendance", student_id, module_id),
                student_id=student_id,
                module_id=module_id,
                attendance_percentage=percentage,
                date=date(2025, 8, 1),
            )
    db.flush()

    # ── Study Sessions ──
    for student_id in ["s-1001", "s-2003", "s-2005"]:
        for subject in ["Database Systems", "Web Development", "Data Structures"]:
            upsert(
                StudySession,
                {"student_id": student_id, "subject": subject, "activity_type": "Revision"},
                id=row_id("study_session", student_id, subject),
                student_id=student_id,
                subject=subject,
                duration_minutes=90,
                activity_type="Revision",
            )
    db.flush()

    # ── Mood Check-ins ──
    mood_data = [
        ("s-1001", 7, 6, "Feeling confident"),
        ("s-1001", 8, 4, "Good week"),
        ("s-1001", 6, 7, "Stressed about exams"),
        ("s-2002", 4, 8, "Struggling with coursework"),
        ("s-2006", 3, 9, "Overwhelmed"),
    ]
    for student_id, mood, stress, note in mood_data:
        upsert(
            MoodCheckin,
            {"student_id": student_id, "notes": note},
            id=row_id("mood_checkin", student_id, note),
            student_id=student_id,
            mood_score=mood,
            stress_level=stress,
            notes=note,
        )
    db.flush()

    # ── Risk Predictions ──
    risks = [
        ("s-1001", 62.0, RiskLevel.MEDIUM, "Attendance dropped 10% and assignment marks decreased in Data Structures."),
        ("s-2002", 82.0, RiskLevel.HIGH, "Attendance below 70%, average mark below 60%, multiple missed deadlines."),
        ("s-2003", 18.0, RiskLevel.LOW, "Consistent attendance and strong assessment performance."),
        ("s-2004", 56.0, RiskLevel.MEDIUM, "Recent quiz scores dropped while study activity reduced."),
        ("s-2005", 22.0, RiskLevel.LOW, "Stable academic performance with high engagement."),
        ("s-2006", 88.0, RiskLevel.HIGH, "Attendance critically low, failed last assessment, low wellbeing scores."),
    ]
    for student_id, score, level, explanation in risks:
        upsert(
            RiskPrediction,
            {"student_id": student_id, "model_version": "gradient_boost_v1.0"},
            id=row_id("risk_prediction", student_id),
            student_id=student_id,
            risk_score=score,
            risk_level=level,
            explanation=explanation,
            model_version="gradient_boost_v1.0",
        )
    db.flush()

    # ── Recommendations ──
    recs = [
        ("s-1001", "attendance", "Attend additional Database Systems tutorials to strengthen practical skills.", "high", "new"),
        ("s-1001", "study", "Increase weekly study sessions by 2 hours to cover Data Structures topics.", "medium", "new"),
        ("s-1001", "wellbeing", "Book a session with the student wellbeing service.", "low", "completed"),
        ("s-2002", "academic", "Enroll in academic support programme for Data Structures.", "high", "new"),
        ("s-2002", "attendance", "Schedule weekly attendance check-in with academic advisor.", "high", "new"),
        ("s-2006", "wellbeing", "Immediate wellbeing referral and catch-up plan needed.", "high", "new"),
    ]
    for student_id, category, message, priority, rec_status in recs:
        upsert(
            Recommendation,
            {"student_id": student_id, "message": message},
            id=row_id("recommendation", student_id, message),
            student_id=student_id,
            category=category,
            message=message,
            priority=priority,
            status=rec_status,
        )

    db.commit()
    if created:
        print("Database seeded. Created: " + ", ".join(f"{name}={count}" for name, count in sorted(created.items())))
    else:
        print("Database already complete. Nothing to add.")
    totals = {
        "users": db.query(User).count(),
        "students": db.query(StudentProfile).count(),
        "modules": db.query(Module).count(),
        "attendance": db.query(Attendance).count(),
        "assessments": db.query(Assessment).count(),
        "study_sessions": db.query(StudySession).count(),
        "mood_checkins": db.query(MoodCheckin).count(),
        "risk_predictions": db.query(RiskPrediction).count(),
        "recommendations": db.query(Recommendation).count(),
    }
    print("Database totals: " + ", ".join(f"{k}={v}" for k, v in totals.items()))

except Exception as e:
    db.rollback()
    print(f"Error seeding database: {e}")
    raise
finally:
    db.close()
