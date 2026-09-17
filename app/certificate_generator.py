import os
from io import BytesIO
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter


class CertificateGenerator:
  def __init__(self, user, test_type, document_type='certificate'):
    self.user = user
    self.test_type = test_type
    self.document_type = document_type
    self.full_name = user.profile.full_name

    if document_type == 'diploma':
      template_filename = 'diplom_tsv_podpis_pechat.pdf'
    else:
      template_filename = 'sertifikat_tsv_podpis_pechat.pdf'

    self.template_path = os.path.join(
      settings.BASE_DIR,
      'app',
      'static',
      'images',
      template_filename
    )

    font_path = os.path.join(
      settings.BASE_DIR,
      'app',
      'static',
      'fonts',
      'lilitaonerus.ttf'
    )
    if os.path.exists(font_path):
      pdfmetrics.registerFont(TTFont('LilitaOne', font_path))
      self.font_name = 'LilitaOne'
    else:
      self.font_name = 'Helvetica'

  def generate(self):
    if not os.path.exists(self.template_path):
      raise FileNotFoundError(f"Шаблон не найден: {self.template_path}")

    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    width, height = A4
    max_width_mm = 180
    font_size = 28

    def get_text_width(text, font_size):
      c.setFont(self.font_name, font_size)
      return c.stringWidth(text, self.font_name, font_size) / 1000 * 25.4

    text_width_mm = get_text_width(self.full_name, font_size)

    # ===== РАЗНЫЕ ПОЗИЦИИ ДЛЯ СЕРТИФИКАТА И ДИПЛОМА =====
    if self.document_type == 'diploma':
      # Настройки для ДИПЛОМА
      x_position = width / 1.40  # Горизонталь
      y_position = height * 0.39  # Вертикаль (чуть выше)
      font_color = '#0D4474'  # Цвет текста (можно изменить)
    else:
      # Настройки для СЕРТИФИКАТА (как было)
      x_position = width / 1.35
      y_position = height * 0.41
      font_color = '#0D4474'
    # =====================================================

    if text_width_mm <= max_width_mm:
      c.setFont(self.font_name, font_size)
      c.setFillColor(colors.HexColor(font_color))
      c.drawCentredString(x_position, y_position, self.full_name)
    else:
      parts = self.full_name.split()

      if len(parts) >= 3:
        first_line = ' '.join(parts[:-1])
        second_line = parts[-1]
      elif len(parts) == 2:
        first_line = parts[0]
        second_line = parts[1]
      else:
        mid = len(self.full_name) // 2
        first_line = self.full_name[:mid]
        second_line = self.full_name[mid:]

      first_width = get_text_width(first_line, font_size - 4)
      second_width = get_text_width(second_line, font_size - 4)

      while first_width > max_width_mm or second_width > max_width_mm:
        font_size -= 2
        first_width = get_text_width(first_line, font_size)
        second_width = get_text_width(second_line, font_size)
        if font_size < 14:
          break

      c.setFont(self.font_name, font_size)
      c.setFillColor(colors.HexColor(font_color))
      c.drawCentredString(x_position, y_position + 8 * mm, first_line)
      c.drawCentredString(x_position, y_position - 8 * mm, second_line)

    c.save()

    with open(self.template_path, 'rb') as f:
      template_pdf = PdfReader(f)
      overlay_pdf = PdfReader(packet)
      writer = PdfWriter()
      template_page = template_pdf.pages[0]
      template_page.merge_page(overlay_pdf.pages[0])
      writer.add_page(template_page)
      result_buffer = BytesIO()
      writer.write(result_buffer)
      result_buffer.seek(0)
      return result_buffer.getvalue()
