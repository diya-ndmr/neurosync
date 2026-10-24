"""Risk-scoring regression tests.

The rule-based score used to cap attendance decline at 30 points and missing work
at 35, both below the MEDIUM threshold of 40. As a result a student whose attendance
had collapsed by 30 percentage points - or who had seven assessments missing - was
still reported as LOW and never reached an advisor queue. Roughly 60 "declining" and
a third of the "highly_disengaged" synthetic students were misclassified.
"""

from lms.workflow_service import classify_risk_trajectory, risk_level_for, score_risk_signal

NO_SIGNAL = {"attendance_change": 0.0, "missing_submissions": 0, "assessment_trend": "stable", "engagement_dropped": False}


def test_trajectory_requires_multiple_declining_signals_for_rapid_deterioration():
    result = classify_risk_trajectory(
        attendance_change=-12,
        assessment_trend="declining",
        engagement_dropped=False,
        engagement_increased=False,
    )

    assert result["trajectory"] == "rapidly_deteriorating"
    assert len(result["evidence"]) == 2


def test_single_declining_signal_is_slow_deterioration():
    result = classify_risk_trajectory(
        attendance_change=-9,
        assessment_trend="stable",
        engagement_dropped=False,
        engagement_increased=False,
    )

    assert result["trajectory"] == "slowly_deteriorating"


def test_improving_trajectory_requires_two_improving_signals():
    result = classify_risk_trajectory(
        attendance_change=0,
        assessment_trend="improving",
        engagement_dropped=False,
        engagement_increased=True,
    )

    assert result["trajectory"] == "improving"
    assert len(result["evidence"]) == 2


def test_mixed_improving_and_declining_signals_are_not_overstated():
    result = classify_risk_trajectory(
        attendance_change=-12,
        assessment_trend="improving",
        engagement_dropped=False,
        engagement_increased=False,
    )

    assert result["trajectory"] == "stable"
    assert len(result["evidence"]) == 2


def test_no_signal_is_low_risk_and_says_so():
    result = score_risk_signal(**NO_SIGNAL)
    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "LOW"
    assert result["evidence"] == ["No significant negative trend was detected in the available LMS indicators."]


def test_severe_attendance_decline_alone_reaches_medium():
    result = score_risk_signal(**{**NO_SIGNAL, "attendance_change": -30.0})
    assert result["risk_level"] == "MEDIUM", result
    assert result["risk_score"] >= 40
    assert "Attendance declined by 30 percentage points" in result["evidence"][0]


def test_seven_missing_submissions_alone_reach_medium():
    result = score_risk_signal(**{**NO_SIGNAL, "missing_submissions": 7})
    assert result["risk_level"] == "MEDIUM", result
    assert result["risk_score"] == 40.0


def test_small_decline_and_few_missing_stay_low():
    result = score_risk_signal(**{**NO_SIGNAL, "attendance_change": -10.0, "missing_submissions": 1})
    assert result["risk_level"] == "LOW", result


def test_combined_signals_reach_high_and_are_capped_at_100():
    result = score_risk_signal(
        attendance_change=-30.0,
        missing_submissions=9,
        assessment_trend="declining",
        engagement_dropped=True,
    )
    assert result["risk_level"] == "HIGH", result
    assert result["risk_score"] == 100.0
    assert len(result["evidence"]) == 4


def test_declining_marks_and_engagement_are_reported():
    result = score_risk_signal(**{**NO_SIGNAL, "assessment_trend": "declining", "engagement_dropped": True})
    assert result["risk_score"] == 40.0
    assert result["risk_level"] == "MEDIUM"
    assert any("assessment marks are lower" in line for line in result["evidence"])
    assert any("LMS activity decreased" in line for line in result["evidence"])


def test_level_thresholds_are_stable():
    assert risk_level_for(0) == "LOW"
    assert risk_level_for(39.9) == "LOW"
    assert risk_level_for(40) == "MEDIUM"
    assert risk_level_for(69.9) == "MEDIUM"
    assert risk_level_for(70) == "HIGH"
