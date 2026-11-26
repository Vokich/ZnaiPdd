from django.urls import path

from app.accounts import api as accounts
from app.classroom import quizzes as classroom_quizzes
from app.classroom import reports as classroom
from app.classroom import runs as classroom_runs
from app.common import http as common
from app.documents import materials as documents
from app.news import api as news_api
from app.organizations import api as organizations
from app.practice import api as practice_api
from app.quizzes import api as quizzes
from app.rankings import api as rating_api
from app.routes import api as route_api
from app.signs import api as signs


urlpatterns = [
    path('classroom/', classroom_runs.classroom),
    path('classroom/tests/', classroom_quizzes.quizzes),
    path('classroom/tests/<int:pk>/', classroom_quizzes.quiz_detail),
    path('classroom/runs/<uuid:pk>/', classroom_runs.teacher_run),
    path('classroom/runs/<uuid:pk>/qr/', classroom_runs.qr_image),
    path('classroom/join/<slug:code>/', classroom_runs.participant),
    path('health/', common.health, name='api_health'),
    path('session/', accounts.session, name='api_session'),
    path('users/', accounts.register, name='api_register'),
    path('municipalities/', organizations.municipalities, name='api_municipalities'),
    path('organizations/', organizations.organizations, name='api_organizations'),
    path('profile/', accounts.profile, name='api_profile'),
    path('profile/results/', quizzes.result_history),
    path('profile/password/', accounts.password, name='api_password'),
    path('tests/<slug:test_type>/', quizzes.test, name='api_test'),
    path('tests/<slug:test_type>/results/', quizzes.test_results, name='api_test_results'),
    path('tests/<slug:test_type>/certificate/', quizzes.certificate, name='api_certificate'),
    path('signs/', signs.signs, name='api_signs'),
    path('signs/<slug:slug>/', signs.sign, name='api_sign'),
    path('signs/<slug:slug>/test/', signs.sign_test, name='api_sign_test'),
    path('lesson-reports/', classroom.lesson_reports, name='api_lesson_reports'),
    path('lesson-reports/options/', classroom.lesson_report_options, name='api_lesson_report_options'),
    path('lesson-reports/<int:report_id>/', classroom.lesson_report, name='api_lesson_report'),
    path('training-material/', documents.training_material, name='api_training_material'),
    path('safe-route/', route_api.route_progress, name='api_route_progress'),
    path('safe-route/<slug:attempt>/memento/', route_api.route_memento, name='api_route_memento'),
    path('competition/', rating_api.competition, name='api_competition'),
    path('rating/', rating_api.rating, name='api_rating'),
    path('practice/', practice_api.exercises, name='api_practice'),
    path('practice/history/', practice_api.practice_history, name='api_practice_history'),
    path('practice/<slug:slug>/', practice_api.exercise, name='api_practice_exercise'),
    path('news/', news_api.news_feed, name='api_news'),
    path('news/next/', news_api.next_event, name='api_next_event'),
    path('news/<slug:slug>/', news_api.news_post, name='api_news_post'),
]
