import uuid
from math import ceil

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator, URLValidator
from django.templatetags.static import static
from datetime import date
from .route_levels import LEVELS
from .starter_road_signs import STARTER_NUMBERS


class Municipality(models.Model):
    code = models.CharField('Код ОКТМО', max_length=8, primary_key=True)
    name = models.CharField('Муниципалитет', max_length=400)

    class Meta:
        ordering = ['name', 'code']
        verbose_name = 'Муниципалитет'
        verbose_name_plural = 'Муниципалитеты'

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField('Название', max_length=300)
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, verbose_name='Муниципалитет')

    class Meta:
        ordering = ['name', 'pk']
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        constraints = [models.UniqueConstraint(fields=['municipality', 'name'], name='organization_municipality_name_uniq')]

    def __str__(self):
        return f'{self.name} ({self.municipality})'


class Profile(models.Model):
    class Role(models.TextChoices):
        CHILD = 'child', 'Пользователь'
        TEACHER = 'teacher', 'Педагог'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        verbose_name='Роль'
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    surname1 = models.CharField(max_length=50, blank=True, verbose_name='Фамилия')
    name = models.CharField(max_length=50, blank=True, verbose_name='Имя')
    surname2 = models.CharField(max_length=50, blank=True, verbose_name='Отчество')
    school = models.CharField(max_length=100, blank=True, verbose_name='Прежнее название учебного заведения')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    region = models.CharField(max_length=400, blank=True, verbose_name='Прежнее название муниципалитета')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Организация')
    municipality = models.ForeignKey(Municipality, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Муниципалитет')
    competition_enabled = models.BooleanField('Участвует в рейтинге', default=False)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return self.full_name or self.user.get_username()

    @property
    def age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    @property
    def full_name(self):
        return ' '.join(filter(None, (self.surname1, self.name)))


class TestResult(models.Model):
    class TestType(models.TextChoices):
        JUNIOR = 'junior', 'Младшая группа'
        TEEN = 'teen', 'Подростковая группа'
        ADULT = 'adult', 'Взрослые'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name='Пользователь')
    test_type = models.CharField(max_length=10, choices=TestType.choices, verbose_name='Тип теста')
    score = models.IntegerField(verbose_name='Набранные баллы')
    total_questions = models.IntegerField(verbose_name='Всего вопросов')
    passing_score = models.IntegerField(verbose_name='Проходной балл')
    passed = models.BooleanField(default=False, verbose_name='Тест пройден')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_test_type_display()} ({self.score}/{self.total_questions})"

    @staticmethod
    def diploma_threshold(total):
        return ceil(total * 4 / 5)

    @property
    def earns_diploma(self):
        return self.passed and self.total_questions > 0 and self.score >= self.diploma_threshold(self.total_questions)


class AgeTestQuestion(models.Model):
    test_type = models.CharField('Возрастная группа', max_length=10, choices=TestResult.TestType.choices)
    number = models.PositiveIntegerField('Номер вопроса', validators=[MinValueValidator(1)])
    text = models.TextField('Вопрос')
    options = models.JSONField('Варианты ответа')
    correct = models.PositiveIntegerField('Номер правильного варианта', validators=[MinValueValidator(1)])
    reference = models.CharField('Пункт ПДД РФ или другого российского нормативного акта', max_length=220)

    class Meta:
        verbose_name = 'Вопрос возрастного теста'
        verbose_name_plural = 'Вопросы возрастных тестов'
        ordering = ['test_type', 'number']
        constraints = [
            models.UniqueConstraint(fields=['test_type', 'number'], name='age_test_question_number_uniq'),
        ]

    def __str__(self):
        return f'{self.get_test_type_display()} · {self.number}. {self.text}'

    def clean(self):
        super().clean()
        if not isinstance(self.options, list) or len(self.options) < 2:
            raise ValidationError({'options': 'Укажите как минимум два варианта ответа.'})
        if any(not isinstance(option, str) or not option.strip() for option in self.options):
            raise ValidationError({'options': 'Каждый вариант должен содержать текст.'})
        if len({option.strip().casefold() for option in self.options}) != len(self.options):
            raise ValidationError({'options': 'Варианты ответа должны различаться.'})
        if self.correct is not None and not 1 <= self.correct <= len(self.options):
            raise ValidationError({'correct': 'Укажите номер одного из вариантов, начиная с 1.'})


class ClassroomQuiz(models.Model):
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    instruction = models.TextField(blank=True)
    questions = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)
    ready = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class ClassroomVersion(models.Model):
    quiz = models.ForeignKey(ClassroomQuiz, on_delete=models.CASCADE, related_name='versions')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=160)
    instruction = models.TextField(blank=True)
    questions = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['quiz', 'number'], name='class_quiz_version_uniq')]


class ClassroomRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.SlugField(blank=True)
    version = models.ForeignKey(ClassroomVersion, null=True, on_delete=models.PROTECT)
    code = models.CharField(max_length=8, unique=True, null=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    deadline = models.DateTimeField(null=True, db_index=True)
    accepting = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True)
    review_until = models.DateTimeField(null=True)
    summary = models.JSONField(default=dict)


class ClassroomAttempt(models.Model):
    run = models.ForeignKey(ClassroomRun, on_delete=models.CASCADE, related_name='attempts')
    browser = models.CharField(max_length=64)
    started = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=list)
    score = models.PositiveSmallIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'browser'], name='class_attempt_browser_uniq')]


class TeacherLessonReport(models.Model):
    classroom = models.OneToOneField(ClassroomRun, null=True, blank=True, on_delete=models.PROTECT, related_name='report')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=False, related_name='lesson_reports', verbose_name='Педагог')
    lesson_date = models.DateField(verbose_name='Дата проведения урока')
    location = models.CharField(max_length=300, blank=True, verbose_name='Площадка или кабинет')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Организация')
    participants_count = models.PositiveIntegerField(verbose_name='Количество участников')
    route_level = models.CharField(
        'Уровень безопасного маршрута', max_length=16, blank=True,
        choices=[(key, level['title']) for key, level in LEVELS.items()],
        help_text='Оставьте пустым для урока без маршрута.',
    )
    practice = models.ForeignKey(
        'PracticeExercise', on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='Задание из практики', related_name='lesson_reports',
    )
    completed_count = models.PositiveIntegerField('Сколько участников завершили задание', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания отчёта')
    certificate_generated = models.BooleanField(default=False, verbose_name='Грамота сгенерирована')

    class Meta:
        verbose_name = 'Отчёт об уроке ПДД'
        verbose_name_plural = 'Отчёты об уроках ПДД'
        ordering = ['-lesson_date', '-pk']
        indexes = [models.Index(fields=['user', '-lesson_date', '-id'], name='report_owner_date_idx')]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(route_level='', practice__isnull=True, completed_count__isnull=True)
                    | models.Q(classroom__isnull=False, route_level='', practice__isnull=True,
                               completed_count__lte=models.F('participants_count'))
                    | models.Q(classroom__isnull=True, route_level__in=tuple(LEVELS), practice__isnull=True, completed_count__isnull=False,
                               completed_count__lte=models.F('participants_count'))
                    | models.Q(classroom__isnull=True, route_level='', practice__isnull=False, completed_count__isnull=False,
                               completed_count__lte=models.F('participants_count'))
                ),
                name='lesson_route_completion_consistent',
            ),
        ]

    def clean(self):
        if self.classroom_id and (self.route_level or self.practice_id):
            raise ValidationError('Отчёт уже привязан к занятию.')
        if self.route_level and self.practice_id:
            raise ValidationError({'practice': 'Выберите одно задание для отчёта.'})
        with_activity = bool(self.route_level or self.practice_id)
        qr = self.classroom_id and self.classroom.version_id
        if not with_activity and not qr and self.completed_count is not None:
            raise ValidationError({'completed_count': 'Укажите количество завершивших только для урока с заданием.'})
        if with_activity and self.completed_count is None:
            raise ValidationError({'completed_count': 'Укажите, сколько участников завершили задание. Если никто, укажите 0.'})
        if self.completed_count is not None and self.participants_count is not None:
            if self.completed_count > self.participants_count:
                raise ValidationError({'completed_count': 'Завершивших не может быть больше, чем участников урока.'})

    def __str__(self):
        return f'{self.user.get_username()} — {self.lesson_date} ({self.participants_count} чел.)'

class Certificate(models.Model):
  class TestType(models.TextChoices):
    JUNIOR = 'junior', 'Младшая группа (8-12)'
    TEEN = 'teen', 'Подростковая группа (12-15)'
    ADULT = 'adult', 'Старшая группа (16-18)'

  class DocumentType(models.TextChoices):
    CERTIFICATE = 'certificate', 'Сертификат'
    DIPLOMA = 'diploma', 'Диплом'

  user = models.ForeignKey(User, on_delete=models.CASCADE)
  test_type = models.CharField(max_length=20, choices=TestResult.TestType.choices)
  document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.CERTIFICATE)
  test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE)
  generated_at = models.DateTimeField(auto_now_add=True)
  download_count = models.IntegerField(default=0)

  class Meta:
    verbose_name = 'Сертификат'
    verbose_name_plural = 'Сертификаты'
    ordering = ['-generated_at']
    unique_together = ['user', 'test_type', 'document_type']

  def clean(self):
    if self.test_result_id and (self.test_result.user_id != self.user_id or self.test_result.test_type != self.test_type):
      raise ValidationError({'test_result': 'Результат должен относиться к владельцу и типу теста этого документа.'})

  def __str__(self):
    return f'{self.user.get_username()} — {self.get_test_type_display()}'


class RoadSign(models.Model):
    class Category(models.TextChoices):
        WARNING = 'warning', 'Предупреждающие'
        PROHIBITING = 'prohibiting', 'Запрещающие'
        MANDATORY = 'mandatory', 'Предписывающие'
        SPECIAL_MANDATORY = 'special_mandatory', 'Особых предписаний'
        INFO = 'info', 'Информационные'
        DOP_INFO = 'dop_info', 'Дополнительной информации'
        SERVICE = 'service', 'Знаки сервиса'
        PRIORITET = 'prioritet', 'Приоритета'


    name = models.CharField('Название', max_length=200)
    slug = models.SlugField(unique=True)
    number = models.CharField(
        'Номер по ПДД', max_length=16, blank=True,
        validators=[RegexValidator(r'^[1-8](?:\.[0-9]+){1,3}$', 'Укажите номер знака, например 5.19.1.')],
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    image = models.ImageField('Изображение', upload_to='signs/', blank=True)
    source_url = models.URLField(
        'Ссылка на правило', max_length=500, blank=True, validators=[URLValidator(schemes=['http', 'https'])],
    )
    image_credit = models.CharField('Источник изображения и условия использования', max_length=300, blank=True)
    reviewed_on = models.DateField('Дата проверки карточки', null=True, blank=True)
    is_published = models.BooleanField('Опубликован', default=False)
    short_description = models.TextField('Краткое описание')
    full_description = models.TextField('Полное описание', blank=True)
    fun_fact = models.TextField('Интересный факт', blank=True)
    question = models.TextField('Вопрос для теста', blank=True)
    answer_options = models.JSONField('Варианты ответов', default=list, blank=True)
    correct_answer = models.IntegerField('Номер правильного ответа', default=1)
    order = models.IntegerField('Порядок', default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Знак ПДД'
        verbose_name_plural = 'Знаки ПДД'
        constraints = [
            models.UniqueConstraint(fields=['number'], condition=~models.Q(number=''), name='road_sign_number_unique'),
        ]

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        if self.number in STARTER_NUMBERS:
            return static(f'road-signs/{self.number}.png')
        return None

    @property
    def has_test(self):
        options = self.answer_options
        return (
            bool(self.question.strip())
            and isinstance(options, list)
            and len(options) >= 2
            and all(isinstance(option, str) and option.strip() for option in options)
            and len({option.strip().casefold() for option in options}) == len(options)
            and isinstance(self.correct_answer, int)
            and 1 <= self.correct_answer <= len(options)
        )

    def clean(self):
        if self.answer_options is None:
            self.answer_options = []
        if not self.is_published:
            return
        errors = {}
        if not self.number:
            errors['number'] = 'Укажите номер опубликованного знака.'
        if not (self.short_description.strip() or self.full_description.strip()):
            errors['short_description'] = 'Добавьте описание знака.'
        if not self.source_url:
            errors['source_url'] = 'Укажите ссылку на правило.'
        if not self.reviewed_on:
            errors['reviewed_on'] = 'Укажите дату проверки карточки.'
        if not self.image_url:
            errors['image'] = 'Добавьте изображение знака.'
        if self.image and not self.image_credit.strip():
            errors['image_credit'] = 'Укажите источник загруженного изображения.'
        if (self.question or self.answer_options) and not self.has_test:
            errors['answer_options'] = 'Для мини-теста нужны вопрос, разные варианты ответа и номер верного варианта.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class UserSignProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sign_progress')
    sign = models.ForeignKey(RoadSign, on_delete=models.CASCADE)
    unlocked = models.BooleanField(default=False)
    test_passed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'sign']
        verbose_name = 'Прогресс по знаку'
        verbose_name_plural = 'Прогресс по знакам'

    def __str__(self):
        return f'{self.user.username} — {self.sign.name}'


class RouteProgress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='route_progress')
    state = models.JSONField()


class RouteResult(models.Model):
    attempt = models.CharField(max_length=32, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='route_results', db_index=False, verbose_name='Пользователь')
    level = models.CharField(max_length=16)
    score = models.IntegerField('Баллы')
    total = models.PositiveSmallIntegerField()
    mistakes = models.PositiveIntegerField('Ошибки')
    rule_reviews = models.JSONField(default=list)
    completed_at = models.DateTimeField('Дата прохождения', auto_now_add=True)

    class Meta:
        verbose_name = 'Результат маршрута'
        verbose_name_plural = 'Результаты маршрутов'
        indexes = [models.Index(fields=['user', 'level', '-score'], name='route_user_level_score_idx')]

    def __str__(self):
        return f'{self.user.get_username()} — {self.score}/{self.total}'

    def clean(self):
        if isinstance(self.score, int) and isinstance(self.total, int) and self.score > self.total:
            raise ValidationError({'score': 'Баллы не могут превышать максимум за маршрут.'})


class PracticeExercise(models.Model):
    class Topic(models.TextChoices):
        CROSSING = 'crossing', 'Переход дороги'
        CYCLING = 'cycling', 'Велосипед'
        SIGNS = 'signs', 'Дорожные знаки'

    class Difficulty(models.TextChoices):
        BASIC = 'basic', 'Начальный'
        ADVANCED = 'advanced', 'Продвинутый'

    title = models.CharField('Название', max_length=150)
    slug = models.SlugField('Адрес задания', unique=True)
    topic = models.CharField('Тема', max_length=12, choices=Topic.choices)
    difficulty = models.CharField('Сложность', max_length=12, choices=Difficulty.choices)
    published_version = models.ForeignKey(
        'PracticeVersion', on_delete=models.SET_NULL, null=True, blank=True,
        editable=False, related_name='+',
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'Задание по ПДД'
        verbose_name_plural = 'Задания по ПДД'

    def __str__(self):
        return self.title

    def clean(self):
        if self.slug == 'history':
            raise ValidationError({'slug': 'Этот адрес занят историей прохождений.'})


class PracticeVersion(models.Model):
    class Kind(models.TextChoices):
        ORDER = 'order', 'Порядок действий'
        PLATES = 'plates', 'Знак и табличка'

    exercise = models.ForeignKey(PracticeExercise, on_delete=models.CASCADE, related_name='versions', verbose_name='Задание')
    kind = models.CharField('Формат', max_length=8, choices=Kind.choices)
    prompt = models.TextField('Условие', max_length=1500)
    explanation = models.TextField('Объяснение', max_length=2000)
    source_url = models.URLField('Ссылка на пункт ПДД', max_length=500, validators=[URLValidator(schemes=['http', 'https'])])
    sign = models.ForeignKey(RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name='Знак')
    plate_a = models.ForeignKey(
        RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+',
        limit_choices_to={'category': RoadSign.Category.DOP_INFO}, verbose_name='Первая табличка',
    )
    plate_b = models.ForeignKey(
        RoadSign, on_delete=models.PROTECT, null=True, blank=True, related_name='+',
        limit_choices_to={'category': RoadSign.Category.DOP_INFO}, verbose_name='Вторая табличка',
    )
    content = models.JSONField(default=dict, editable=False)
    published_at = models.DateTimeField('Опубликована', null=True, blank=True, editable=False)
    withdrawn_at = models.DateTimeField('Отозвана', null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Версия задания'
        verbose_name_plural = 'Версии заданий'

    def __str__(self):
        return f'{self.exercise} · № {self.pk}' if self.pk else str(self.exercise)


class PracticeResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_results')
    version = models.ForeignKey(PracticeVersion, on_delete=models.PROTECT, related_name='results')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at', '-id']
        constraints = [models.UniqueConstraint(fields=['user', 'version'], name='unique_practice_completion')]
        verbose_name = 'Результат практики'
        verbose_name_plural = 'Результаты практики'


class NewsPost(models.Model):
    class Kind(models.TextChoices):
        NEWS = 'news', 'Новость'
        EVENT = 'event', 'Анонс'
        RESULT = 'result', 'Итоги'

    TIMEZONES = (
        ('Europe/Moscow', 'Москва'), ('Europe/Kaliningrad', 'Калининград'),
        ('Europe/Samara', 'Самара'), ('Asia/Yekaterinburg', 'Екатеринбург'),
        ('Asia/Omsk', 'Омск'), ('Asia/Krasnoyarsk', 'Красноярск'), ('Asia/Irkutsk', 'Иркутск'),
        ('Asia/Yakutsk', 'Якутск'), ('Asia/Vladivostok', 'Владивосток'),
        ('Asia/Magadan', 'Магадан'), ('Asia/Kamchatka', 'Камчатка'),
    )
    title = models.CharField('Заголовок', max_length=160)
    slug = models.SlugField('Адрес публикации', unique=True)
    kind = models.CharField('Тип', max_length=8, choices=Kind.choices, default=Kind.NEWS)
    summary = models.CharField('Краткое описание', max_length=280, blank=True)
    body = models.TextField('Текст публикации', max_length=12000, blank=True)
    cover = models.ImageField('Обложка', upload_to='news/', blank=True)
    cover_credit = models.CharField('Источник обложки и условия использования', max_length=250, blank=True)
    signs = models.ManyToManyField(RoadSign, blank=True, verbose_name='Связанные знаки')
    exercises = models.ManyToManyField(PracticeExercise, blank=True, verbose_name='Связанные задания')
    published_at = models.DateTimeField('Опубликована', null=True, blank=True, editable=False)
    starts_at = models.DateTimeField('Начало (по Москве)', null=True, blank=True)
    timezone_name = models.CharField('Часовой пояс показа', max_length=24, choices=TIMEZONES, default='Europe/Moscow')
    venue = models.CharField('Место или онлайн-формат', max_length=200, blank=True)
    audience = models.CharField('Для кого', max_length=120, blank=True)
    organizer = models.CharField('Организатор', max_length=150, blank=True)
    registration_deadline = models.DateTimeField('Регистрация до (по Москве)', null=True, blank=True)
    registration_url = models.URLField('Внешняя ссылка для регистрации', max_length=500, blank=True,
                                       validators=[URLValidator(schemes=['https', 'http'])])
    cancelled = models.BooleanField('Мероприятие отменено', default=False)

    class Meta:
        ordering = ['-published_at', '-id']
        verbose_name = 'Публикация'
        verbose_name_plural = 'Новости и мероприятия'

    def __str__(self):
        return self.title

    def publication_errors(self):
        errors = {}
        if not self.body.strip():
            errors['body'] = 'Добавьте текст публикации.'
        if not self.summary.strip():
            errors['summary'] = 'Добавьте краткое описание.'
        if self.cover and not self.cover_credit.strip():
            errors['cover_credit'] = 'Укажите источник обложки и условия использования.'
        if self.kind == self.Kind.EVENT:
            for field in ('starts_at', 'venue', 'audience', 'organizer'):
                if not getattr(self, field):
                    errors[field] = 'Заполните это поле для анонса.'
            if self.registration_deadline and not self.registration_url:
                errors['registration_url'] = 'Добавьте ссылку, если указан срок регистрации.'
            elif self.registration_deadline and self.starts_at and self.registration_deadline > self.starts_at:
                errors['registration_deadline'] = 'Срок регистрации должен быть до начала встречи.'
        return errors

    def clean(self):
        if self.slug == 'next':
            raise ValidationError({'slug': 'Этот адрес занят блоком ближайшего мероприятия.'})
        if self.published_at and (errors := self.publication_errors()):
            raise ValidationError(errors)


class ContentImage(models.Model):
    alt = models.CharField('Описание для скринридера', max_length=200, blank=True)
    caption = models.CharField('Подпись под изображением', max_length=250, blank=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        abstract = True
        ordering = ['order', 'pk']
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'

    def __str__(self):
        return self.caption or self.alt or 'Изображение'


class NewsImage(ContentImage):
    post = models.ForeignKey(NewsPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Файл', upload_to='news/gallery/')


class PracticeImage(ContentImage):
    version = models.ForeignKey(PracticeVersion, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Файл', upload_to='practice/')
