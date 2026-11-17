from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import RoadSign
from app.starter_road_signs import RULEBOOK, STARTER_SIGNS


class Command(BaseCommand):
    help = 'Добавляет стартовые карточки в справочник знаков ПДД.'

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for order, sign in enumerate(STARTER_SIGNS, start=1):
            number, name, category, page, description, question, correct, first, second = sign
            slug = 'pdd-' + number.replace('.', '-')
            if RoadSign.objects.filter(number=number).exists() or RoadSign.objects.filter(slug=slug).exists():
                continue
            card = RoadSign(
                slug=slug, number=number, name=name, category=category, order=order,
                source_url=f'{RULEBOOK}#page={page}', image_credit='Приложение 1 к ПДД РФ',
                reviewed_on=date(2026, 11, 16), is_published=True, short_description=description,
                question=question, answer_options=[correct, first, second], correct_answer=1,
            )
            card.full_clean()
            card.save()
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Добавлено карточек: {created}.'))
