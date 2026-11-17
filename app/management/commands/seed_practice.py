from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.models import NewsPost, PracticeExercise, PracticeVersion, RoadSign
from app.practice import publish_practice
from app.starter_practice import MEANINGS, ORDER_LESSONS, PLATE_GROUPS, PLATE_LESSONS
from app.starter_road_signs import PRACTICE_SIGNS, RULEBOOK


class Command(BaseCommand):
    help = 'Добавляет 10 стартовых упражнений и информационную публикацию о разделе.'

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('seed_road_signs', stdout=self.stdout)
        for order, (number, title, category, page, description) in enumerate(PRACTICE_SIGNS, start=20):
            if not RoadSign.objects.filter(number=number).exists():
                card = RoadSign(
                    number=number, slug='pdd-' + number.replace('.', '-'), name=title, category=category,
                    order=order, short_description=description, image_credit='Приложение 1 к ПДД РФ',
                    source_url=f'{RULEBOOK}#page={page}', reviewed_on=date(2026, 11, 16), is_published=True,
                )
                card.full_clean()
                card.save()
        signs = {sign.number: sign for sign in RoadSign.objects.filter(number__in={
            *(row[4] for row in ORDER_LESSONS), *(row[2] for row in PLATE_LESSONS),
            *(number for group in PLATE_GROUPS.values() for number in group['plates']),
        })}
        created = 0
        for slug, title, topic, difficulty, number, page, prompt, explanation, cards, orders in ORDER_LESSONS:
            created += self.create(slug, title, topic, difficulty, kind=PracticeVersion.Kind.ORDER,
                                   source_url=f'{RULEBOOK}#page={page}', sign=signs[number],
                                   prompt=prompt, explanation=explanation, content={'cards': cards, 'orders': orders})
        for slug, title, number, group_id, meaning in PLATE_LESSONS:
            group = PLATE_GROUPS[group_id]
            first, second = group['plates']
            created += self.create(
                slug, title, PracticeExercise.Topic.SIGNS, group['difficulty'], kind=PracticeVersion.Kind.PLATES,
                source_url=f"{RULEBOOK}#page={group['page']}", sign=signs[number],
                plate_a=signs[first], plate_b=signs[second],
                prompt=group['prompt'], explanation=group['explanation'],
                content={'meanings': MEANINGS, 'conditions': group['options'], 'right_meanings': [meaning],
                         'right_a': [1], 'right_b': [2]},
            )
        post, added = NewsPost.objects.get_or_create(slug='practice-opened', defaults={
            'title': 'Открылась «Практика ПДД»', 'kind': NewsPost.Kind.NEWS,
            'summary': 'Попробуйте два формата заданий о переходах, знаках и табличках.',
            'body': ('В «Практике ПДД» можно собирать порядок действий в дорожной ситуации '
                     'и сравнивать, как таблички меняют значение знака.\n\n'
                     'После проверки сайт покажет объяснение и ссылку на правило. Начать можно с задания о переходе на зелёный.'),
            'published_at': timezone.now(),
        })
        if added:
            post.exercises.add(*PracticeExercise.objects.filter(slug__in=('cross-on-green', 'stop-calendar')))
        self.stdout.write(self.style.SUCCESS(f'Добавлено упражнений: {created}.'))

    def create(self, slug, title, topic, difficulty, **version):
        exercise, created = PracticeExercise.objects.get_or_create(
            slug=slug, defaults={'title': title, 'topic': topic, 'difficulty': difficulty},
        )
        if not created:
            return 0
        version = PracticeVersion.objects.create(exercise=exercise, **version)
        publish_practice(version.pk)
        return 1
