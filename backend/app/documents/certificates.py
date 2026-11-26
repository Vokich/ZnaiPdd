from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from django.db import transaction
from django.db.models import F
from reportlab.lib.pagesizes import A4, landscape

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.models import Certificate, TestResult


class CertificateGenerator:
    def __init__(self, user, test_type, document_type='certificate'):
        profile = getattr(user, 'profile', None)
        parts = (profile.surname1, profile.name, profile.surname2) if profile else ()
        self.full_name = ' '.join(filter(None, parts)) or user.get_full_name() or user.get_username()
        self.title = 'Диплом' if document_type == 'diploma' else 'Сертификат'
        self.group = TestResult.TestType(test_type).label

    def generate(self):
        font = 'LilitaOne'
        if font not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font, settings.BASE_DIR / 'app/static/fonts/lilitaonerus.ttf'))

        width, height = landscape(A4)
        output = BytesIO()
        pdf = Canvas(output, pagesize=(width, height))
        pdf.setTitle(f'{self.title} — Знай ПДД')
        pdf.setAuthor('Образовательная платформа «Знай ПДД»')
        pdf.setFillColor(HexColor('#FAF8F1'))
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        pdf.setStrokeColor(HexColor('#164A66'))
        pdf.setLineWidth(2)
        pdf.roundRect(26, 26, width - 52, height - 52, 12)
        pdf.setFont(font, 15)
        pdf.setFillColor(HexColor('#164A66'))
        pdf.drawCentredString(width / 2, height - 100, 'ЗНАЙ ПДД')
        pdf.setFont(font, 52)
        pdf.drawCentredString(width / 2, height - 180, self.title)
        pdf.setFont(font, 16)
        pdf.drawCentredString(width / 2, height * .38, 'За успешное прохождение теста по правилам дорожного движения')
        pdf.drawCentredString(width / 2, height * .32, self.group)
        pdf.setFont(font, 14)
        pdf.drawCentredString(width / 2, 81, 'Выдано платформой «Знай ПДД»')
        font_size = 28
        max_width = width * .45
        lines = [self.full_name]
        if pdf.stringWidth(self.full_name, font, font_size) > max_width:
            words = self.full_name.split()
            if len(words) > 1:
                splits = [(' '.join(words[:i]), ' '.join(words[i:])) for i in range(1, len(words))]
                lines = min(splits, key=lambda pair: max(pdf.stringWidth(line, font, font_size) for line in pair))
            longest = max(pdf.stringWidth(line, font, font_size) for line in lines)
            font_size *= min(1, max_width / longest)

        pdf.setFont(font, font_size)
        pdf.setFillColor(HexColor('#0D4474'))
        baseline = height * .51 + (len(lines) - 1) * font_size * .55
        for index, line in enumerate(lines):
            pdf.drawCentredString(width * .5, baseline - index * font_size * 1.1, line)
        pdf.save()

        return output.getvalue()


def award_download(result):
    kind = Certificate.DocumentType.DIPLOMA if result.earns_diploma else Certificate.DocumentType.CERTIFICATE
    generator = CertificateGenerator(result.user, result.test_type, kind)
    document = generator.generate()
    with transaction.atomic():
        award, _ = Certificate.objects.get_or_create(
            user=result.user, test_type=result.test_type, document_type=kind, defaults={'test_result': result})
        Certificate.objects.filter(pk=award.pk).update(test_result=result, download_count=F('download_count') + 1)
    return FileResponse(BytesIO(document), as_attachment=True, filename=f'{kind.label}_{generator.full_name}.pdf',
                        content_type='application/pdf')
