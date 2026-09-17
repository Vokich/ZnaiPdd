"""
URL configuration for pdd_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('age/child/', views.child, name='child'),
    path('age/teen/', views.teen, name='teen'),
    path('age/adults/', views.adults, name='adults'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.logout_form, name='logout'),
    path('reg/', views.reg, name='reg'),
    path('test-result-child/', views.test_result_child, name='result_child'),
    path('test-result-teen/', views.test_result_teen, name='result_teen'),
    path('test-result-adult/', views.test_result_adult, name='result_adults'),
    path('pdd-teacher/', views.pdd_teacher, name='pdd-teacher'),
    path('certificate/<str:test_type>/', views.generate_certificate, name='generate_certificate'),
    path('download-training/', views.download_training_file, name='download_training'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password/', views.profile_password_change, name='profile_password'),
]
