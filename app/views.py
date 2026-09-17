from django.contrib.auth import login as auth_login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from io import BytesIO
import os
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from .forms import (
  UserRegistrationForm,
  LoginForm,
  TeenPddTestForm,
  JuniorPddTestForm,
  AdultPddTestForm,
  TeacherLessonReportForm,
  UserProfileForm,
  PasswordChangeForm,
)


from .forms import (
  UserRegistrationForm,
  LoginForm,
  TeenPddTestForm,
  JuniorPddTestForm,
  AdultPddTestForm,
  TeacherLessonReportForm
)
from .models import TestResult, TeacherLessonReport, Certificate
from .certificate_generator import CertificateGenerator


def is_child(user):
  return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'child'


def is_teacher(user):
  return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'teacher'


def index(request):
  return render(request, 'index.html')


@user_passes_test(is_child)
def child(request):
  if request.method == 'POST':
    form = JuniorPddTestForm(request.POST)
    if form.is_valid():
      result = form.check_answers(passing_score=18)
      TestResult.objects.create(
        user=request.user,
        test_type=TestResult.TestType.JUNIOR,
        score=result['score'],
        total_questions=result['total'],
        passing_score=result['passing_score'],
        passed=result['passed']
      )
      request.session['result_child'] = {
        'score': result['score'],
        'total': result['total'],
        'passing_score': result['passing_score'],
        'passed': result['passed']
      }
      return redirect('result_child')
    else:
      return render(request, 'child.html', {'form': form})
  else:
    form = JuniorPddTestForm()
  return render(request, 'child.html', {'form': form})


@login_required
def test_result_child(request):
  result = request.session.get('result_child')
  if not result:
    return redirect('child')

  context = {'result': result}
  if result.get('passed', False):
    context['has_certificate'] = Certificate.objects.filter(
      user=request.user,
      test_type=TestResult.TestType.JUNIOR
    ).exists()

  return render(request, 'pdd_child_success.html', context)


@user_passes_test(is_child)
def teen(request):
  if request.method == 'POST':
    form = TeenPddTestForm(request.POST)
    if form.is_valid():
      result = form.check_answers(passing_score=18)
      TestResult.objects.create(
        user=request.user,
        test_type=TestResult.TestType.TEEN,
        score=result['score'],
        total_questions=result['total'],
        passing_score=result['passing_score'],
        passed=result['passed']
      )
      request.session['result_teen'] = {
        'score': result['score'],
        'total': result['total'],
        'passing_score': result['passing_score'],
        'passed': result['passed']
      }
      return redirect('result_teen')
    else:
      return render(request, 'teen.html', {'form': form})
  else:
    form = TeenPddTestForm()
  return render(request, 'teen.html', {'form': form})


@login_required
def test_result_teen(request):
  result = request.session.get('result_teen')
  if not result:
    return redirect('teen')

  context = {'result': result}

  # Если тест сдан, добавляем информацию о сертификате
  if result.get('passed', False):
    context['has_certificate'] = Certificate.objects.filter(
      user=request.user,
      test_type=TestResult.TestType.TEEN
    ).exists()

  return render(request, 'pdd_teen_success.html', context)


@user_passes_test(is_child)
def adults(request):
  if request.method == 'POST':
    form = AdultPddTestForm(request.POST)
    if form.is_valid():
      result = form.check_answers(passing_score=18)
      TestResult.objects.create(
        user=request.user,
        test_type=TestResult.TestType.ADULT,
        score=result['score'],
        total_questions=result['total'],
        passing_score=result['passing_score'],
        passed=result['passed']
      )
      request.session['result_adults'] = {
        'score': result['score'],
        'total': result['total'],
        'passing_score': result['passing_score'],
        'passed': result['passed']
      }
      return redirect('result_adults')
    else:
      return render(request, 'adults.html', {'form': form})
  else:
    form = AdultPddTestForm()
  return render(request, 'adults.html', {'form': form})


@login_required
def test_result_adult(request):
  result = request.session.get('result_adults')
  if not result:
    return redirect('adults')

  context = {'result': result}
  if result.get('passed', False):
    context['has_certificate'] = Certificate.objects.filter(
      user=request.user,
      test_type=TestResult.TestType.ADULT
    ).exists()

  return render(request, 'pdd_adult_success.html', context)


@user_passes_test(is_teacher)
def pdd_teacher(request):
  reports = TeacherLessonReport.objects.filter(user=request.user).order_by('-lesson_date')
  if request.method == 'POST':
    form = TeacherLessonReportForm(request.POST)
    if form.is_valid():
      report = form.save(commit=False)
      report.user = request.user
      report.save()
      messages.success(request, 'Отчёт успешно сохранён!')
      return redirect('pdd-teacher')
    else:
      messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
  else:
    form = TeacherLessonReportForm()

  context = {
    'form': form,
    'reports': reports,
  }
  return render(request, 'pdd-teacher.html', context)


@ensure_csrf_cookie
def reg(request):
  if request.method == 'POST':
    form = UserRegistrationForm(request.POST)
    if form.is_valid():
      user = form.save()
      auth_login(request, user)
      messages.success(request, 'Регистрация успешно завершена!')
      return redirect('index')
    else:
      messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
  else:
    form = UserRegistrationForm()
  return render(request, 'registration.html', {'form': form})


def user_login(request):
  if request.method == 'POST':
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
      auth_login(request, user)
      messages.success(request, f'Добро пожаловать, {user.username}!')
      return redirect('index')
    else:
      messages.error(request, 'Неверный логин или пароль.')

  form = LoginForm()
  return render(request, 'login.html', {'form': form})


def logout_form(request):
  logout(request)
  messages.info(request, 'Вы вышли из системы.')
  return redirect('index')


@login_required
def generate_certificate(request, test_type):
  if not is_child(request.user):
    messages.error(request, 'Доступ запрещен. Сертификаты доступны только для учеников.')
    return redirect('index')

  if test_type not in ['junior', 'teen', 'adult']:
    messages.error(request, 'Неверный тип теста.')
    return redirect('index')

  try:
    test_result = TestResult.objects.filter(
      user=request.user,
      test_type=test_type,
      passed=True
    ).latest('completed_at')
  except TestResult.DoesNotExist:
    messages.error(request, 'Сначала успешно сдайте тест!')
    return redirect('index')

  score = test_result.score
  if score >= 24:
    document_type = 'diploma'
    document_name = 'Диплом'
  elif score >= 18:
    document_type = 'certificate'
    document_name = 'Сертификат'
  else:
    messages.error(request, 'Недостаточно баллов для получения документа.')
    return redirect('index')

  certificate, created = Certificate.objects.get_or_create(
    user=request.user,
    test_type=test_type,
    document_type=document_type,
    defaults={
      'test_result': test_result
    }
  )

  if not created and certificate.test_result != test_result:
    certificate.test_result = test_result
    certificate.save()

  certificate.download_count += 1
  certificate.save()

  try:
    generator = CertificateGenerator(request.user, test_type, document_type)
    pdf_content = generator.generate()
    full_name = request.user.profile.full_name
    filename = f"{document_name}_{full_name}.pdf"
    response = FileResponse(
      BytesIO(pdf_content),
      content_type='application/pdf',
      filename=filename
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
  except Exception as e:
    messages.error(request, f'Ошибка при генерации документа: {str(e)}')
    return redirect('index')

@login_required
def certificate_history(request):
  if not is_child(request.user):
    messages.error(request, 'Доступ запрещен.')
    return redirect('index')
  certificates = Certificate.objects.filter(
    user=request.user
  ).select_related('test_result').order_by('-generated_at')
  return render(request, 'certificate_history.html', {
    'certificates': certificates
  })

def download_training_file(request):
  file_path = os.path.join(
    settings.BASE_DIR,
    'app',
    'static',
    'images',
    'академия ворд (2).docx'
  )
  if os.path.exists(file_path):
    return FileResponse(
      open(file_path, 'rb'),
      content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      filename='академия_ворд.docx'
    )
  else:
    from django.http import HttpResponse
    return HttpResponse("Файл не найден", status=404)

def privacy_policy(request):
  return render(request, 'privacy_policy.html')


@login_required
def profile_view(request):
  profile = request.user.profile
  test_results = TestResult.objects.filter(user=request.user).order_by('-completed_at')[:5]
  reports_count = TeacherLessonReport.objects.filter(user=request.user).count() if profile.role == 'teacher' else 0

  context = {
    'profile': profile,
    'test_results': test_results,
    'reports_count': reports_count,
  }
  return render(request, 'profile.html', context)


@login_required
def profile_edit(request):
  profile = request.user.profile

  if request.method == 'POST':
    form = UserProfileForm(request.POST, instance=request.user, profile_instance=profile)
    if form.is_valid():
      form.save()
      messages.success(request, 'Данные профиля успешно обновлены!')
      return redirect('profile')
    else:
      messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
  else:
    form = UserProfileForm(instance=request.user, profile_instance=profile)

  return render(request, 'profile_edit.html', {'form': form, 'profile': profile})


@login_required
def profile_password_change(request):
  if request.method == 'POST':
    form = PasswordChangeForm(request.POST, user=request.user)
    if form.is_valid():
      user = form.save()
      update_session_auth_hash(request, user)  # ← ЭТО ГЛАВНОЕ
      messages.success(request, 'Пароль успешно изменён!')
      return redirect('profile')
    else:
      messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
  else:
    form = PasswordChangeForm(user=request.user)

  return render(request, 'profile_password.html', {'form': form})
