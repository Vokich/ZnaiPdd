from io import BytesIO

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


class CertificateGenerator:
    def __init__(self, user, test_type, document_type='certificate'):
        self.full_name = user.profile.full_name
        filename = 'diplom_tsv_podpis_pechat.pdf' if document_type == 'diploma' else 'sertifikat_tsv_podpis_pechat.pdf'
        self.template_path = settings.BASE_DIR / 'app/static/images' / filename

    def generate(self):
        font = 'LilitaOne'
        if font not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font, settings.BASE_DIR / 'app/static/fonts/lilitaonerus.ttf'))

        page = PdfReader(self.template_path).pages[0]
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        overlay = BytesIO()
        pdf = Canvas(overlay, pagesize=(width, height))
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
        baseline = height * .582 + (len(lines) - 1) * font_size * .55
        for index, line in enumerate(lines):
            pdf.drawCentredString(width * .512, baseline - index * font_size * 1.1, line)
        pdf.save()

        page.merge_page(PdfReader(overlay).pages[0])
        writer = PdfWriter()
        writer.add_page(page)
        result = BytesIO()
        writer.write(result)
        return result.getvalue()
