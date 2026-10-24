from __future__ import annotations

import random
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.engine import make_url

from lms.database import (
    CONFIGURED_LMS_DATABASE_URL,
    LMSSessionLocal,
    LMSBase,
    build_lms_session_factory,
    ensure_lms_db,
    get_lms_database_url,
)
from lms.models import (
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    AttendanceSession,
    LMSActivity,
    Lecturer,
    Module,
    ModuleEnrolment,
    DatasetImport,
    Programme,
    Quiz,
    QuizAttempt,
    ResourceActivity,
    StaffMapping,
    StudentMapping,
    Submission,
    Student,
)

FIRST_NAMES = [
    "Ava", "Noah", "Mila", "Leo", "Ivy", "Theo", "Zoe", "Kai", "Luna", "Eli",
    "Sofia", "Arlo", "Ruby", "Mason", "Nia", "Finn", "Elena", "Riley", "Jude", "Harper",
    "Lucas", "Maya", "Miles", "Avery", "Layla", "Ezra", "Iris", "Hugo", "Clara", "Soren",
    "Amelia", "Nora", "Owen", "Sadie", "Felix", "Grace", "Julian", "Hazel", "Asher", "Scarlett",
    "Milo", "Naomi", "Tobin", "Olivia", "Isaac", "Piper", "Wesley", "Chloe", "Dylan", "Eden",
    "Emmett", "Ariana", "Caleb", "Freya", "Ronan", "Genevieve", "Adrian", "Sienna", "Carter", "Leah",
    "Jonah", "Violet", "Samuel", "Ella", "Wyatt", "Bianca", "Victor", "Gavin", "Maren", "Sage",
    "Jasmine", "Aiden", "Delia", "Hudson", "Aurora", "Silas", "Claire", "Nathan", "Skye", "Omar",
    "Maeve", "Rowan", "Lila", "Evan", "Dahlia", "Nolan", "Alina", "Caden", "Vivian", "Maddox",
    "Selena", "Nicolas", "Coralie", "Beckett", "Rosalie", "Alec", "Tara", "Colin", "Mina", "Declan",
    "Inez", "Jeremiah", "Nova", "Gideon", "Anya", "Dorian", "Priya", "Liam", "Zara", "Kian",
    "Aisha", "Daniel", "Amina", "Lucy", "Yusuf", "Ella", "Nadia", "Hannah", "Noah", "Maya",
]

SURNAMES = [
    "Patel", "Nguyen", "Santos", "Brown", "Morris", "Hughes", "Johnson", "Kim", "Ali", "Garcia",
    "Davis", "Clark", "Evans", "Murphy", "Leclerc", "Baker", "Rossi", "Meyer", "Ahmed", "Booker",
    "Chen", "Roberts", "Wilson", "Turner", "Price", "Bell", "Carter", "Martin", "Campbell", "James",
    "Bennett", "Wright", "Young", "Rivera", "Lopez", "Ward", "King", "Reed", "Cooper", "Hayes",
    "Ross", "Brooks", "Coleman", "Foster", "Russell", "Perry", "Sullivan", "Torres", "Powell", "Mills",
    "Stevens", "Harris", "Knight", "Barker", "Walters", "Cruz", "Shaw", "Griffin", "Mendoza", "Graham",
    "Howard", "Fisher", "Scott", "Hill", "Allen", "Hansen", "Stone", "Mason", "Bryant", "Parker",
    "Gibson", "Jordan", "Fernandez", "Dixon", "Phillips", "Fox", "Alexander", "Henderson", "Nelson",
    "Cunningham", "Payne", "Burns", "Lane", "Richards", "Simmons", "Peters", "Singh", "Thompson", "Cohen",
    "Ramirez", "Borges", "Nolan", "Hawkins", "Murray", "Fitzgerald", "Morrison", "Reynolds", "Weber",
    "Anderson", "Moore", "Taylor", "Thomas", "Walker", "Lewis", "Robinson", "Green", "Hall"
]

PROGRAMMES = [
    ("BSC-IT", "BSc in Information Technology", "School of Computing", "Undergraduate"),
    ("BSC-CS", "BSc in Computer Science", "School of Computing", "Undergraduate"),
    ("BSC-DS", "BSc in Data Science", "School of Analytics", "Undergraduate"),
    ("BENG-SE", "BEng in Software Engineering", "School of Engineering", "Undergraduate"),
    ("BSC-CY", "BSc in Cybersecurity", "School of Computing", "Undergraduate"),
    ("MSc-AI", "MSc in Artificial Intelligence", "School of Computing", "Postgraduate"),
]

MODULE_BLUEPRINTS = {
    "BSC-IT": [("IT101", "Programming Fundamentals", 20, 1), ("IT102", "Database Systems", 20, 2), ("IT203", "Web Technologies", 20, 2), ("IT204", "Computer Networks", 20, 3), ("IT305", "Software Engineering", 20, 3)],
    "BSC-CS": [("CS101", "Algorithms", 20, 1), ("CS102", "Computer Architecture", 20, 1), ("CS203", "Operating Systems", 20, 2), ("CS204", "Artificial Intelligence", 20, 2), ("CS305", "Distributed Systems", 20, 3)],
    "BSC-DS": [("DS101", "Statistics", 20, 1), ("DS102", "Data Visualisation", 20, 1), ("DS203", "Machine Learning", 20, 2), ("DS204", "Data Mining", 20, 2), ("DS305", "Big Data Analytics", 20, 3)],
    "BENG-SE": [("SE101", "Engineering Design", 20, 1), ("SE102", "Requirements Analysis", 20, 1), ("SE203", "Software Testing", 20, 2), ("SE204", "Systems Design", 20, 2), ("SE305", "Project Management", 20, 3)],
    "BSC-CY": [("CY101", "Cyber Foundations", 20, 1), ("CY102", "Network Security", 20, 1), ("CY203", "Digital Forensics", 20, 2), ("CY204", "Risk Management", 20, 2), ("CY305", "Secure Systems", 20, 3)],
    "MSc-AI": [("AI501", "Machine Learning Foundations", 30, 1), ("AI502", "Natural Language Processing", 30, 1), ("AI603", "Deep Learning", 30, 2), ("AI604", "AI Ethics", 30, 2), ("AI705", "Research Methods", 30, 3)],
}

LECTURERS = [
    ("Aisha", "Rahman", "Computer Science"), ("Daniel", "Meyer", "Cybersecurity"), ("Nadia", "Santos", "Data Science"),
    ("Ethan", "Brooks", "Software Engineering"), ("Olivia", "Chen", "Analytics"), ("Marcus", "Lopez", "Systems"),
    ("Priya", "Sharma", "Software Engineering"), ("Frank", "Hughes", "Networking"), ("Sara", "Nguyen", "AI"),
    ("Martin", "Coleman", "Computing"), ("Anita", "Patel", "Data Science"), ("Ibrahim", "Ali", "Security"),
]

GROUP_SIZES = {"stable": 325, "improving": 75, "declining": 60, "highly_disengaged": 25, "complex": 15}


def _student_id(index: int) -> str:
    return f"STU{index:04d}"


def _safe_number(value: float) -> float:
    return round(float(max(0.0, min(100.0, value))), 2)


class _DeterministicIds:
    


    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def next(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:08d}"


def _build_group_sequence() -> list[str]:
    seq: list[str] = []
    for group, count in GROUP_SIZES.items():
        seq.extend([group] * count)
    rng = random.Random(42)
    rng.shuffle(seq)
    return seq


def _attendance_status(group: str, week_index: int, rng: random.Random) -> str:
    if group == "highly_disengaged":
        if week_index > 5 and rng.random() < 0.55:
            return "ABSENT"
        if rng.random() < 0.12:
            return "LATE"
        return "PRESENT"
    if group == "declining":
        if week_index > 6 and rng.random() < 0.35:
            return "ABSENT"
        if week_index > 4 and rng.random() < 0.15:
            return "LATE"
        return "PRESENT"
    if group == "improving":
        if week_index > 10 and rng.random() < 0.08:
            return "ABSENT"
        if rng.random() < 0.08:
            return "LATE"
        return "PRESENT"
    if rng.random() < 0.06:
        return "EXCUSED"
    if rng.random() < 0.08:
        return "LATE"
    return "PRESENT"


def _assessment_percentage(group: str, rng: random.Random, progress: float = 0.0) -> float:
    """Mark for one assessment; ``progress`` runs 0 (first) to 1 (last) of the semester.

    Marks have to move over time, otherwise the "recent marks are lower than the
    previous period" risk criterion can never fire and every cohort reads as stable.
    """
    if group == "stable":
        value = rng.uniform(64, 88)
    elif group == "improving":
        value = rng.uniform(48, 82) + 14 * progress
    elif group == "declining":
        value = rng.uniform(45, 78) - 18 * progress
    elif group == "highly_disengaged":
        value = rng.uniform(28, 60) - 14 * progress
    else:
        value = rng.uniform(50, 90)
    return max(0.0, min(100.0, value))


def _generate_programmes(db) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for code, _, _, _ in PROGRAMMES:
        programme = Programme(programme_id=f"PRG-{code}", programme_code=code, programme_name=next(name for c, name, _, _ in PROGRAMMES if c == code), faculty=next(faculty for c, _, faculty, _ in PROGRAMMES if c == code), level=next(level for c, _, _, level in PROGRAMMES if c == code))
        db.add(programme)
    db.flush()
    for code, _, _, _ in PROGRAMMES:
        p = db.query(Programme).filter(Programme.programme_code == code).one()
        mapping[code] = p.programme_id
    return mapping


def _generate_lecturers(db) -> list[Lecturer]:
    lecturers: list[Lecturer] = []
    for idx, (first_name, surname, department) in enumerate(LECTURERS, start=1):
        lecturer = Lecturer(lecturer_id=f"LEC{idx:03d}", first_name=first_name, surname=surname, email=f"{first_name.lower()}.{surname.lower()}@university.edu", department=department)
        db.add(lecturer)
        lecturers.append(lecturer)
    db.flush()
    db.add(StaffMapping(app_user_email="lecturer@university.edu", lecturer_id=lecturers[0].lecturer_id))
    db.flush()
    return lecturers


def _generate_modules(db, programme_map: dict[str, str], lecturers: list[Lecturer]) -> dict[str, list[str]]:
    programme_modules: dict[str, list[str]] = {}
    counter = 1
    for code, _, _, _ in PROGRAMMES:
        modules: list[str] = []
        lecturer = lecturers[(counter - 1) % len(lecturers)]
        for module_code, module_name, credits, semester in MODULE_BLUEPRINTS[code]:
            module = Module(module_id=f"MOD{counter:04d}", programme_id=programme_map[code], module_code=module_code, module_name=module_name, credits=credits, semester=semester, lecturer_id=lecturer.lecturer_id)
            db.add(module)
            modules.append(module.module_id)
            counter += 1
        programme_modules[code] = modules
    db.flush()
    return programme_modules


def _generate_students(db, programme_map: dict[str, str], group_sequence: list[str]):
    students: list[Student] = []
    codes = [code for code, _, _, _ in PROGRAMMES]
    for index in range(1, 501):
        code = codes[(index - 1) % len(codes)]
        first_name = FIRST_NAMES[(index * 3) % len(FIRST_NAMES)]
        surname = SURNAMES[(index * 5) % len(SURNAMES)]
        student = Student(
            student_id=_student_id(index),
            first_name=first_name,
            surname=surname,
            institutional_email=f"{_student_id(index).lower()}@student.neurosync.demo",
            programme_id=programme_map[code],
            year_of_study=min(4, ((index - 1) % 4) + 1),
            semester=(index % 2) + 1,
            behaviour_group=group_sequence[index - 1],
            enrolment_status="ACTIVE",
        )
        db.add(student)
        students.append(student)
    db.flush()
    db.add(StudentMapping(app_user_email="sarah@university.edu", student_id=_student_id(1)))
    db.flush()
    return students


def _generate_enrolments(db, students: list[Student], programme_modules: dict[str, list[str]], programme_map: dict[str, str], rng: random.Random, ids: _DeterministicIds):
    for student in students:
        programme_code = next(code for code, _, _, _ in PROGRAMMES if programme_map[code] == student.programme_id)
        modules = programme_modules[programme_code][:]
        rng.shuffle(modules)
        selected = modules[: min(4, len(modules))]
        for module_id in selected:
            db.add(ModuleEnrolment(enrolment_id=ids.next("ENR"), student_id=student.student_id, module_id=module_id, status="ENROLLED"))
    db.flush()


def _generate_attendance(db, students: list[Student], rng: random.Random, ids: _DeterministicIds):
    start = date.today() - timedelta(weeks=13)
    for student in students:
        group = student.behaviour_group
        for week_index in range(14):
            session_date = start + timedelta(weeks=week_index)
            for enrolment in student.module_enrolments:
                status = _attendance_status(group, week_index, rng)
                session = AttendanceSession(session_id=ids.next("ATS"), module_id=enrolment.module_id, session_date=session_date, session_type="LECTURE")
                db.add(session)
                db.add(AttendanceRecord(attendance_id=ids.next("ATT"), student_id=student.student_id, module_id=enrolment.module_id, session=session, session_date=session_date, status=status))
    db.flush()


def _generate_assessments(db, ids: _DeterministicIds):
    mapping: dict[str, list[Assessment]] = {}
    for module in db.query(Module).all():
        items: list[Assessment] = []
        weights = [25.0, 25.0, 25.0, 25.0]
        for idx, a_type in enumerate(["ASSIGNMENT", "TEST", "PROJECT", "EXAM"]):
            assessment = Assessment(assessment_id=ids.next("ASM"), module_id=module.module_id, title=f"{a_type} {idx + 1}", assessment_type=a_type, weight=weights[idx], maximum_mark=100.0, due_date=date.today() - timedelta(days=84) + timedelta(days=idx * 28))
            db.add(assessment)
            items.append(assessment)
        db.flush()
        mapping[module.module_id] = items
    return mapping


def _generate_mark_results(db, students: list[Student], assessments_by_module: dict[str, list[Assessment]], rng: random.Random, ids: _DeterministicIds):
    for student in students:
        group = student.behaviour_group
        for enrolment in student.module_enrolments:
            module_assessments = assessments_by_module.get(enrolment.module_id, [])
            for index, assessment in enumerate(module_assessments):
                progress = index / (len(module_assessments) - 1) if len(module_assessments) > 1 else 0.0
                percentage = _assessment_percentage(group, rng, progress)
                if assessment.due_date > date.today():
                    status = "NOT_YET_DUE"
                    mark = 0.0
                elif group == "highly_disengaged" and rng.random() < 0.45:
                    status = "MISSING"
                    mark = 0.0
                elif assessment.due_date < date.today() and rng.random() < 0.15:
                    status = "LATE"
                    mark = percentage * 0.9
                else:
                    status = "SUBMITTED"
                    mark = percentage
                submission_date = assessment.due_date if status in {"SUBMITTED", "LATE"} else None
                db.add(AssessmentResult(result_id=ids.next("RES"), student_id=student.student_id, assessment_id=assessment.assessment_id, mark=_safe_number(mark), percentage=_safe_number(percentage), submission_date=submission_date, status=status))
                submitted_at = datetime.combine(submission_date, datetime.min.time(), tzinfo=timezone.utc) if submission_date else None
                db.add(Submission(submission_id=ids.next("SUB"), student_id=student.student_id, assessment_id=assessment.assessment_id, submitted_at=submitted_at, status=status))
    db.flush()


def _generate_quizzes(db, students: list[Student], rng: random.Random, ids: _DeterministicIds):
    for module in db.query(Module).all():
        for week in [2, 5, 8, 11]:
            q = Quiz(quiz_id=ids.next("QZ"), module_id=module.module_id, title=f"Quiz {week}", available_date=date.today() - timedelta(weeks=12 - week), maximum_score=100.0)
            db.add(q)
    db.flush()
    for student in students:
        group = student.behaviour_group
        for enrolment in student.module_enrolments:
            quizzes = db.query(Quiz).filter(Quiz.module_id == enrolment.module_id).all()
            for quiz in quizzes:
                attempts = 2 if group in {"declining", "improving"} else 1 if group == "stable" else 1 if group == "complex" else 1
                for attempt_number in range(1, attempts + 1):
                    percentage = rng.uniform(40, 90) if group in {"stable", "improving"} else rng.uniform(20, 75)
                    started = datetime.combine(quiz.available_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9 + attempt_number)
                    completed = started + timedelta(minutes=int(percentage / 3) + 12)
                    db.add(QuizAttempt(attempt_id=ids.next("QAT"), student_id=student.student_id, quiz_id=quiz.quiz_id, attempt_number=attempt_number, score=_safe_number(percentage), percentage=_safe_number(percentage), started_at=started, completed_at=completed, duration=int((completed - started).total_seconds() / 60)))
    db.flush()


def _generate_activity(db, students: list[Student], rng: random.Random, ids: _DeterministicIds):
    start = datetime.combine(date.today() - timedelta(weeks=13), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=8)
    activity_types = ["LOGIN", "VIEW_MODULE", "VIEW_RESOURCE", "VIEW_ASSESSMENT", "DISCUSSION_VIEW", "DOWNLOAD_RESOURCE"]
    for student in students:
        group = student.behaviour_group
        for week in range(14):
            login_count = 5 if group == "stable" else 4 if group == "improving" else 3 if group == "declining" else 1 if group == "highly_disengaged" else 4
            for idx in range(login_count):
                module_id = student.module_enrolments[idx % len(student.module_enrolments)].module_id if student.module_enrolments else None
                ts = start + timedelta(weeks=week, minutes=idx * 40 + rng.randint(5, 35))
                activity = rng.choice(activity_types)
                db.add(LMSActivity(activity_id=ids.next("ACT"), student_id=student.student_id, timestamp=ts, activity_type=activity, module_id=module_id, session_duration=max(5, rng.randint(10, 65))))
                if activity in {"VIEW_RESOURCE", "DOWNLOAD_RESOURCE"}:
                    db.add(ResourceActivity(resource_activity_id=ids.next("RSC"), student_id=student.student_id, timestamp=ts, activity_type=activity, module_id=module_id, resource_name=f"resource_{rng.randint(1, 18)}.pdf"))
    db.flush()


def _duplicate_primary_keys(db, model, column_name: str) -> list[str]:
    duplicates = (
        db.query(getattr(model, column_name))
        .group_by(getattr(model, column_name))
        .having(func.count() > 1)
        .all()
    )
    return [row[0] for row in duplicates]


def validate_generated_data(db) -> dict[str, Any]:
    student_count = db.query(Student).count()
    if student_count != 500:
        raise ValueError(f"Expected 500 students, found {student_count}")
    ids = [s.student_id for s in db.query(Student.student_id).all()]
    if ids != [f"STU{idx:04d}" for idx in range(1, 501)]:
        raise ValueError("Student IDs are not sequential STU0001..STU0500")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate student IDs detected")
    if db.query(AssessmentResult).filter((AssessmentResult.mark < 0) | (AssessmentResult.mark > 100)).count() > 0:
        raise ValueError("Assessment marks are out of range")
    if db.query(QuizAttempt).filter((QuizAttempt.percentage < 0) | (QuizAttempt.percentage > 100)).count() > 0:
        raise ValueError("Quiz scores are out of range")
    if db.query(LMSActivity).filter(LMSActivity.session_duration < 0).count() > 0:
        raise ValueError("Negative session durations detected")
    total_weights = db.query(Assessment.module_id, func.sum(Assessment.weight).label("w")).group_by(Assessment.module_id).all()
    if any(entry[1] > 100 for entry in total_weights):
        raise ValueError("Assessment weights exceed a valid module total")
    duplicate_checks = (
        (AttendanceSession, "session_id"),
        (AttendanceRecord, "attendance_id"),
        (Assessment, "assessment_id"),
        (AssessmentResult, "result_id"),
        (Quiz, "quiz_id"),
        (QuizAttempt, "attempt_id"),
        (Submission, "submission_id"),
        (LMSActivity, "activity_id"),
        (ModuleEnrolment, "enrolment_id"),
    )
    for model, column_name in duplicate_checks:
        duplicates = _duplicate_primary_keys(db, model, column_name)
        if duplicates:
            raise ValueError(f"Duplicate {column_name} values detected in {model.__tablename__}: {duplicates[:5]}")
    return {"student_count": student_count, "ids_ok": True}


def generate_mock_lms(db_path: Optional[str] = None, recreate: bool = False) -> Dict[str, Any]:
    if db_path is not None:
        db_file = Path(ensure_lms_db(db_path)).resolve()
        target_url = f"sqlite:///{db_file}"
    elif CONFIGURED_LMS_DATABASE_URL is None:
        db_file = Path(ensure_lms_db(None)).resolve()
        target_url = f"sqlite:///{db_file}"
    else:
        target_url = get_lms_database_url()
        db_file = None
        if target_url.startswith("sqlite:"):
            from sqlalchemy.engine import make_url

            configured_path = Path(make_url(target_url).database or "").expanduser()
            if not configured_path.is_absolute():
                configured_path = (Path.cwd() / configured_path).resolve()
            configured_path.parent.mkdir(parents=True, exist_ok=True)
            db_file = configured_path
    if recreate and db_file is not None and db_file.exists():
        db_file.unlink()
    engine, session_factory = build_lms_session_factory(database_url=target_url)
    LMSBase.metadata.create_all(bind=engine)
    db = session_factory()
    try:
        if recreate:
            LMSBase.metadata.drop_all(bind=engine)
            LMSBase.metadata.create_all(bind=engine)
        programme_map = _generate_programmes(db)
        lecturers = _generate_lecturers(db)
        programme_modules = _generate_modules(db, programme_map, lecturers)
        group_sequence = _build_group_sequence()
        students = _generate_students(db, programme_map, group_sequence)
        rng = random.Random(42)
        ids = _DeterministicIds()
        _generate_enrolments(db, students, programme_modules, programme_map, rng, ids)
        _generate_attendance(db, students, rng, ids)
        assessments_by_module = _generate_assessments(db, ids)
        _generate_mark_results(db, students, assessments_by_module, rng, ids)
        _generate_quizzes(db, students, rng, ids)
        _generate_activity(db, students, rng, ids)
        db.commit()
        validate_generated_data(db)
        summary = {
            "database_path": str(db_file) if db_file is not None else target_url,
            "student_count": db.query(Student).count(),
            "programme_count": db.query(Programme).count(),
            "module_count": db.query(Module).count(),
            "lecturer_count": db.query(Lecturer).count(),
            "assessment_count": db.query(Assessment).count(),
            "quiz_count": db.query(Quiz).count(),
            "lms_activity_count": db.query(LMSActivity).count(),
            "resource_activity_count": db.query(ResourceActivity).count(),
            "student_ids_min": "STU0001",
            "student_ids_max": "STU0500",
            "behaviour_group_counts": dict(Counter(group_sequence)),
        }
        return summary
    finally:
        db.close()


def lms_dataset_is_seeded(db_path: Optional[str] = None) -> bool:
    """Return True when the LMS database already holds imported or seeded data."""
    owned_engine = None
    if db_path is None:
        session_factory = LMSSessionLocal
    else:
        target = Path(ensure_lms_db(db_path))
        if not target.exists():
            return False
        owned_engine, session_factory = build_lms_session_factory(str(target))
    try:
        db = session_factory()
        try:
            return db.query(Student).count() > 0 or db.query(DatasetImport).count() > 0
        finally:
            db.close()
    except Exception:
        # Missing tables (first run) or an unreadable file behave as "not seeded".
        return False
    finally:
        if owned_engine is not None:
            owned_engine.dispose()


def ensure_mock_lms_seeded(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Generate the synthetic dataset only when the Mock LMS database is empty.

    Returns the generation summary when data was created, otherwise ``None`` so
    repeated application starts remain cheap and idempotent.
    """
    if lms_dataset_is_seeded(db_path):
        return None
    return generate_mock_lms(db_path=db_path, recreate=True)


if __name__ == "__main__":
    print(generate_mock_lms(recreate=True))
