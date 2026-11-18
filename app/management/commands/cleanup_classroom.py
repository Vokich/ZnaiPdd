from time import sleep

from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from app.classroom_runs import refresh_run
from app.models import ClassroomRun


class Command(BaseCommand):
    help = 'Закрывает истёкшие QR-сессии и удаляет временные ответы после срока разбора.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')

    def handle(self, *args, **options):
        while True:
            now = timezone.now()
            runs = ClassroomRun.objects.filter(
                Q(closed_at__isnull=True, deadline__lte=now) |
                Q(review_until__lte=now, attempts__isnull=False)
            ).values_list('pk', flat=True).distinct()
            for pk in runs.iterator(chunk_size=100):
                with transaction.atomic():
                    run = ClassroomRun.objects.select_for_update().get(pk=pk)
                    refresh_run(run)
            if not options['watch']:
                break
            close_old_connections()
            sleep(60)
