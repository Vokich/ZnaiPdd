from django.urls import path

from . import api


urlpatterns = [
    path('health/', api.health, name='api_health'),
    path('session/', api.session, name='api_session'),
    path('users/', api.register, name='api_register'),
    path('municipalities/', api.municipalities, name='api_municipalities'),
    path('profile/', api.profile, name='api_profile'),
    path('profile/password/', api.password, name='api_password'),
    path('tests/<slug:test_type>/', api.test, name='api_test'),
    path('tests/<slug:test_type>/results/', api.test_results, name='api_test_results'),
    path('tests/<slug:test_type>/certificate/', api.certificate, name='api_certificate'),
    path('signs/', api.signs, name='api_signs'),
    path('signs/<slug:slug>/', api.sign, name='api_sign'),
    path('signs/<slug:slug>/test/', api.sign_test, name='api_sign_test'),
    path('lesson-reports/', api.lesson_reports, name='api_lesson_reports'),
    path('training-material/', api.training_material, name='api_training_material'),
]
