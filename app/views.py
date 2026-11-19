from django.contrib.auth import login as auth_login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import Http404, HttpResponse, FileResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from io import BytesIO
import os
import random
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError, transaction
from django.core.exceptions import PermissionDenied
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


from .access import account_role, can_submit_lesson_reports, is_child
from .models import TestResult, Certificate
from .certificate_generator import CertificateGenerator
from .models import RoadSign
from django.shortcuts import get_object_or_404
from .municipalities import search_municipalities
from .sign_catalog import catalog_signs, learned_sign_ids, mark_sign_learned, published_signs

def get_profile(user):
    return getattr(user, 'profile', None)

def index(request):
  return render(request, 'index.html')


def age_test_page(request, form_class, template, session_key, result_view):
  form = form_class(request.POST if request.method == 'POST' else None)
  if not form.questions_data:
    return render(request, template, {'form': form, 'unavailable': True}, status=404)
  if request.method == 'POST' and request.POST.get('revision') != form.revision:
    return render(request, template, {'form': form_class(), 'updated': True}, status=409)
  if form.is_valid():
    score = form.check_answers()
    result = TestResult.objects.create(
      user=request.user, test_type=form.test_type, score=score['score'], total_questions=score['total'],
      passing_score=score['passing_score'], passed=score['passed'],
    )
    request.session[session_key] = {
      'score': result.score, 'total': result.total_questions, 'passing_score': result.passing_score,
      'passed': result.passed, 'diploma_score': result.diploma_threshold(result.total_questions),
    }
    return redirect(result_view)
  return render(request, template, {'form': form})


@user_passes_test(is_child)
def child(request):
  return age_test_page(request, JuniorPddTestForm, 'child.html', 'result_child', 'result_child')


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
  return age_test_page(request, TeenPddTestForm, 'teen.html', 'result_teen', 'result_teen')


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
  return age_test_page(request, AdultPddTestForm, 'adults.html', 'result_adults', 'result_adult')


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


@login_required
def pdd_teacher(request):
  if not can_submit_lesson_reports(request.user):
    if request.method == 'POST':
      raise PermissionDenied
    return render(request, 'pdd-teacher.html')
  reports = request.user.lesson_reports.select_related('organization__municipality', 'practice')
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


@require_GET
def municipality_search(request):
    results, more = search_municipalities(request.GET.get('q', ''))
    return JsonResponse({'results': results, 'more': more}, json_dumps_params={'ensure_ascii': False})


@ensure_csrf_cookie
def reg(request):
  if request.method == 'POST':
    form = UserRegistrationForm(request.POST)
    if form.is_valid():
      try:
        user = form.save()
      except IntegrityError:
        if not User.objects.filter(username=form.cleaned_data['username']).exists():
          raise
        form.add_error('username', 'Пользователь с таким логином уже существует.')
      else:
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

  if test_result.earns_diploma:
    document_type = 'diploma'
    document_name = 'Диплом'
  elif test_result.score >= test_result.passing_score:
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
    profile = get_profile(request.user)
    test_results = request.user.test_results.all()[:5] if is_child(request.user) else []
    can_submit_reports = can_submit_lesson_reports(request.user)

    context = {
        'profile': profile,
        'test_results': test_results,
        'account_role': account_role(request.user),
        'reports_count': request.user.lesson_reports.count() if can_submit_reports else 0,
    }
    return render(request, 'profile.html', context)


@login_required
def profile_edit(request):
    profile = get_profile(request.user)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                form = UserProfileForm(request.POST, instance=user, profile_instance=get_profile(user))
                if form.is_valid():
                    form.save()
                    return redirect('profile')
        except IntegrityError:
            if not User.objects.exclude(pk=request.user.pk).filter(username=form.cleaned_data['username']).exists():
                raise
            form.add_error('username', 'Пользователь с таким логином уже существует.')
    else:
        form = UserProfileForm(instance=request.user, profile_instance=profile)

    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})


@login_required
def profile_password_change(request):
  if request.method == 'POST':
    form = PasswordChangeForm(request.POST, user=request.user)
    if form.is_valid():
      user = form.save()
      update_session_auth_hash(request, user)  
      messages.success(request, 'Пароль успешно изменён!')
      return redirect('profile')
    else:
      messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
  else:
    form = PasswordChangeForm(user=request.user)

  return render(request, 'profile_password.html', {'form': form})


def signs_landing(request):
    total = published_signs().count()
    return render(request, 'znaki/landing.html', {'total': total})


@never_cache
def signs_list(request):
    category = request.GET.get('category', '')
    query = request.GET.get('q', '')[:120]

    context = {
        'signs': catalog_signs(category, query),
        'categories': RoadSign.Category.choices,
        'current_category': category,
        'query': query,
        'unlocked_ids': learned_sign_ids(request.user),
    }
    return render(request, 'znaki/list.html', context)


@never_cache
def sign_detail(request, slug):
    sign = get_object_or_404(published_signs(), slug=slug)
    learned = request.user.is_authenticated and request.user.sign_progress.filter(sign=sign, unlocked=True).exists()
    return render(request, 'znaki/detail.html', {'sign': sign, 'learned': learned})


@login_required
@never_cache
def sign_test(request, slug):
    sign = get_object_or_404(published_signs(), slug=slug)
    if not sign.has_test:
        raise Http404
    if request.user.sign_progress.filter(sign=sign, unlocked=True).exists():
        return redirect('sign_detail', slug=slug)
    error = None
    if request.method == 'POST':
        try:
            answer = int(request.POST.get('answer', 0))
        except (TypeError, ValueError):
            answer = 0
        if answer == sign.correct_answer:
            mark_sign_learned(request.user, sign)
            return redirect('sign_detail', slug=slug)
        else:
            error = 'Неверный ответ. Попробуйте ещё раз.'
    options_with_indices = list(enumerate(sign.answer_options, start=1))
    random.shuffle(options_with_indices)

    context = {
        'sign': sign,
        'options': options_with_indices,  
        'error': error,
    }
    return render(request, 'znaki/test.html', context)
