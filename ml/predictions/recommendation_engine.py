"""
NeuroSync Recommendation Engine
================================
Rule-based recommendation generator driven by student risk factors.
Produces targeted academic, attendance, wellbeing and study
recommendations with priorities.
"""

from typing import List


def generate_recommendations(features: dict, risk_level: str) -> List[dict]:
    """Generate a list of recommendations based on risk factors."""
    recommendations = []

    attendance = features.get("attendance_percentage", 100)
    avg_mark = features.get("academic_average", 100)
    study_hours = features.get("study_hours_weekly", 15)
    stress = features.get("stress_average", 1)
    mood = features.get("mood_average", 5)
    failed = features.get("failed_module_count", 0)

    # Attendance recommendations
    if attendance < 70:
        recommendations.append({
            "category": "attendance",
            "message": "Schedule a meeting with your lecturer and improve attendance to stay on track.",
            "priority": "high",
        })
    elif attendance < 85:
        recommendations.append({
            "category": "attendance",
            "message": "Monitor attendance and aim for at least 85% to reduce academic risk.",
            "priority": "medium",
        })

    # Academic recommendations
    if avg_mark < 50:
        recommendations.append({
            "category": "academic",
            "message": "Attend additional academic support sessions and review course materials.",
            "priority": "high",
        })
    elif avg_mark < 65:
        recommendations.append({
            "category": "academic",
            "message": "Join a study group and book office hours with your lecturers.",
            "priority": "medium",
        })

    if failed > 0:
        recommendations.append({
            "category": "academic",
            "message": "Create a catch-up plan for failed modules and contact your academic advisor.",
            "priority": "high",
        })

    # Study behaviour recommendations
    if study_hours < 10:
        recommendations.append({
            "category": "study",
            "message": "Increase weekly study hours by 2 hours and schedule regular revision sessions.",
            "priority": "medium",
        })
    if features.get("lms_activity_score", 100) < 50:
        recommendations.append({
            "category": "study",
            "message": "Engage more with the learning management system and complete weekly activities.",
            "priority": "medium",
        })

    # Wellbeing recommendations
    if stress > 8:
        recommendations.append({
            "category": "wellbeing",
            "message": "Consider accessing student wellbeing support services for stress management.",
            "priority": "high",
        })
    if mood < 4:
        recommendations.append({
            "category": "wellbeing",
            "message": "Book a wellbeing check-in with the student counselling service.",
            "priority": "high",
        })

    # If risk is elevated but no specific factor triggered
    if risk_level in ("HIGH", "MEDIUM") and not recommendations:
        recommendations.append({
            "category": "study",
            "message": "Meet with your academic advisor to review your progress and set goals.",
            "priority": "medium",
        })

    # Positive reinforcement
    if risk_level == "LOW":
        recommendations.append({
            "category": "study",
            "message": "Keep up the good work — maintain current study habits and engagement.",
            "priority": "low",
        })

    return recommendations


if __name__ == "__main__":
    demo = {
        "attendance_percentage": 62.0,
        "academic_average": 48.0,
        "study_hours_weekly": 6.0,
        "stress_average": 9,
        "mood_average": 4,
        "failed_module_count": 2,
        "lms_activity_score": 40.0,
    }
    for rec in generate_recommendations(demo, "HIGH"):
        print(f"[{rec['priority'].upper()}] ({rec['category']}) {rec['message']}")

