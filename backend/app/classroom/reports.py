from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.accounts.access import require_report_access
from app.classroom.forms import TeacherLessonReportForm
from app.classroom.lessons import run_title
from app.common.http import checked, object_data
from app.models import ClassroomRun, TeacherLessonReport
from app.organizations.api import organization_data
from app.practice.service import public_exercises
from app.routes.levels import published_levels


def report_data(report):
    run = report.classroom
    classroom = None
    if run:
        classroom = {'id': run.pk, 'title': run_title(run), 'lesson': run.lesson,
                     'submitted': run.summary.get('submitted')}
    return {
        'classroom': classroom,
        'id': report.pk,
        'lesson_date': report.lesson_date,
        'location': report.location,
        'participants_count': report.participants_count,
        'route_level': report.route_level,
        'practice': {'id': report.practice_id, 'title': report.practice.title, 'slug': report.practice.slug}
                     if report.practice else None,
        'completed_count': report.completed_count,
        'organization': organization_data(report.organization) if report.organization else None,
    }


@never_cache
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_report_options(request):
    require_report_access(request.user)
    routes = [{'id': key, 'title': level['title']} for key, level in published_levels().items()]
    if request.query_params.get('include') == 'practice':
        return Response({'routes': routes, 'practice': list(public_exercises().values('id', 'slug', 'title'))})
    return Response(routes)


@never_cache
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lesson_reports(request):
    require_report_access(request.user)
    if request.method == 'GET':
        reports = request.user.lesson_reports.select_related('organization__municipality', 'practice', 'classroom__version')
        return Response([report_data(report) for report in reports])
    data = object_data(request)
    report = TeacherLessonReport(user=request.user)
    with transaction.atomic():
        if 'classroom' in data:
            try:
                run_id = UUID(str(data['classroom']))
            except ValueError:
                raise ValidationError({'detail': 'Выберите занятие.'})
            run = get_object_or_404(ClassroomRun.objects.select_for_update(), pk=run_id, owner=request.user)
            existing = TeacherLessonReport.objects.filter(classroom=run).first()
            if existing:
                return Response(report_data(existing))
            if run.version_id and not run.closed_at:
                raise ValidationError({'detail': 'Сначала закройте сессию теста.'})
            report.classroom = run
            if run.lesson:
                run.closed_at = timezone.now()
                run.save(update_fields=['closed_at'])
        report = checked(TeacherLessonReportForm(data, instance=report)).save()
    return Response(report_data(report), status=201)


@never_cache
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def lesson_report(request, report_id):
    require_report_access(request.user)
    reports = request.user.lesson_reports.select_related('organization__municipality', 'practice')
    if request.method == 'GET':
        return Response(report_data(get_object_or_404(reports, pk=report_id)))
    data = object_data(request).copy()
    with transaction.atomic():
        report = get_object_or_404(TeacherLessonReport.objects.select_for_update(), user=request.user, pk=report_id)
        for field in ('lesson_date', 'location', 'participants_count', 'route_level'):
            data.setdefault(field, getattr(report, field))
        data.setdefault('practice', report.practice_id)
        data.setdefault('completed_count', report.completed_count if report.classroom_id or data['route_level'] or data['practice'] else None)
        data.setdefault('organization', report.organization_id)
        report = checked(TeacherLessonReportForm(data, instance=report)).save()
    return Response(report_data(report))
