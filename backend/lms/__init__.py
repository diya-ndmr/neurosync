"""Mock LMS package for synthetic academic data generation and access."""

from .database import ensure_lms_db, get_lms_db, lms_engine, LMSBase
from .generator import generate_mock_lms
from .models import ApprovedLeaveRecord, DatasetImport, MonthlyAttendanceSummary

__all__ = [
    "generate_mock_lms",
    "ensure_lms_db",
    "get_lms_db",
    "lms_engine",
    "LMSBase",
    "MonthlyAttendanceSummary",
    "ApprovedLeaveRecord",
    "DatasetImport",
]
