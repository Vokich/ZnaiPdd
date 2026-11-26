from collections import Counter, defaultdict
from tempfile import TemporaryFile

from django.http import FileResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


class ReportSheet:
    def __init__(self, book, title, headings, widths):
        self.book, self.title, self.headings, self.widths = book, title, headings, widths
        self.start()

    def start(self):
        self.sheet = self.book.create_sheet(self.title)
        self.sheet.freeze_panes = 'A2'
        for i, width in enumerate(self.widths, 1):
            self.sheet.column_dimensions[get_column_letter(i)].width = width
        self.sheet.append([self.cell(value, True) for value in self.headings])
        self.count = 1

    def cell(self, value, heading=False):
        if isinstance(value, str):
            value = ILLEGAL_CHARACTERS_RE.sub('', value)
        cell = WriteOnlyCell(self.sheet, value=value)
        if isinstance(value, str):
            cell.data_type = 's'
        if heading:
            cell.font = Font(bold=True, color='164A66')
        return cell

    def append(self, values):
        if self.count == 1048576:
            self.finish()
            self.start()
        self.sheet.append([self.cell(value) for value in values])
        self.count += 1

    def finish(self):
        self.sheet.auto_filter.ref = f'A1:{get_column_letter(len(self.headings))}{self.count}'


def export_attempts(queryset):
    book = Workbook(write_only=True)
    attempts = ReportSheet(book, 'Попытки', ('Попытка', 'Дата (МСК)', 'ID участника', 'Участник', 'Организация', 'Раздел',
        'Задание', 'Версия', 'Баллы', 'Максимум', 'Результат, %', 'Детализация'), (13, 22, 15, 34, 38, 24, 42, 18, 12, 12, 16, 20))
    answers = ReportSheet(book, 'Ответы', ('Попытка', 'Участник', 'Организация', 'Задание', '№', 'Вопрос',
        'Выбранный ответ', 'Правильный ответ', 'Верно'), (13, 34, 38, 34, 8, 72, 52, 52, 12))
    summary = ReportSheet(book, 'Сводка по вопросам', ('Раздел', 'Задание', 'Версия', 'Вопрос', 'Верный ответ',
        'Ответов', 'Верных', 'Верных, %', 'Частая ошибка'), (22, 36, 18, 68, 45, 12, 12, 14, 45))
    totals = defaultdict(lambda: [0, 0, Counter()])
    for obj in queryset.select_related('user__profile').iterator(chunk_size=250):
        profile = getattr(obj.user, 'profile', None)
        name = ' '.join(filter(None, (profile.surname1, profile.name, profile.surname2))) if profile else ''
        name = name or (obj.user.username if obj.user_id else 'Без имени')
        attempts.append((obj.pk, timezone.localtime(obj.completed_at).replace(tzinfo=None), obj.user_id, name,
                         obj.organization, obj.get_kind_display(), obj.title, obj.version, obj.score, obj.total,
                         round(100 * obj.score / obj.total, 2) if obj.total else None,
                         'Есть' if obj.answers else 'Нет детализации'))
        for i, row in enumerate(obj.answers, 1):
            answers.append((obj.pk, name, obj.organization, obj.title, i, row['question'], row['selected'],
                            row['expected'], 'Да' if row['correct'] else 'Нет'))
            group = totals[(obj.get_kind_display(), obj.task, obj.title, obj.version, row['question'], row['expected'])]
            group[0] += 1
            group[1] += int(row['correct'])
            if not row['correct']:
                group[2][row['selected']] += 1
    for (kind, task, title, version, question, expected), (n, correct, errors) in totals.items():
        summary.append((kind, title, version, question, expected, n, correct, round(100 * correct / n, 2),
                        errors.most_common(1)[0][0] if errors else ''))
    for sheet in (attempts, answers, summary):
        sheet.finish()
    output = TemporaryFile()
    try:
        book.save(output)
        output.seek(0)
        return FileResponse(output, as_attachment=True, filename='platform-statistics.xlsx')
    except Exception:
        output.close()
        raise
