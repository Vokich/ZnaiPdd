"""Register the domain models under the existing Django app label."""

from app.accounts.models import Profile, TeacherContact
from app.classroom.models import (
    ClassroomAttempt,
    ClassroomQuiz,
    ClassroomRun,
    ClassroomVersion,
    TeacherLessonReport,
)
from app.documents.models import Certificate
from app.editorial.models import ContentImage
from app.news.models import NewsImage, NewsPost
from app.organizations.models import Municipality, Organization
from app.practice.models import PracticeExercise, PracticeImage, PracticeResult, PracticeVersion
from app.quizzes.models import AgeTestQuestion, TestResult
from app.reporting.models import PlatformAttempt
from app.routes.models import RouteProgress, RouteResult, RouteSceneContent
from app.signs.models import RoadSign, UserSignProgress

__all__ = [
    "AgeTestQuestion",
    "Certificate",
    "ClassroomAttempt",
    "ClassroomQuiz",
    "ClassroomRun",
    "ClassroomVersion",
    "ContentImage",
    "Municipality",
    "NewsImage",
    "NewsPost",
    "Organization",
    "PlatformAttempt",
    "PracticeExercise",
    "PracticeImage",
    "PracticeResult",
    "PracticeVersion",
    "Profile",
    "RoadSign",
    "RouteProgress",
    "RouteResult",
    "RouteSceneContent",
    "TeacherContact",
    "TeacherLessonReport",
    "TestResult",
    "UserSignProgress",
]
