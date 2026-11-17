from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .route_levels import LEVELS
from .safe_routes import district, rule_url


def route_pdf(state, result):
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=A4)
    pdf.setTitle('Безопасный маршрут — учебная памятка')
    font = 'RouteCyrillic'
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, settings.BASE_DIR / 'app/static/fonts/lilitaonerus.ttf'))

    points, edges = district(state['level'], state['seed'], state['version'])
    trail = list(zip(state['path'], state['path'][1:]))
    locations = {key: (49 + node['x'] * 4.9, 708 - node['y'] * 1.62) for key, node in points.items()}
    pdf.setFont(font, 24)
    pdf.drawString(48, 786, 'Безопасный маршрут')
    pdf.setFont(font, 13)
    pdf.drawString(48, 761, LEVELS[state['level']]['title'] + ' · Учебный сценарий')
    pdf.drawString(48, 737, f"Баллы {result['score']} из {result['total']}   ·   Ошибок: {result['mistakes']}   ·   Открыто правил: {result['rules_opened']}")
    for first, second in edges:
        chosen = (first, second) in trail or (second, first) in trail
        pdf.setStrokeColor(colors.HexColor('#1b447d') if chosen else colors.HexColor('#a9b6c6'))
        pdf.setLineWidth(3 if chosen else 1)
        pdf.line(*locations[first], *locations[second])

    pdf.setFont(font, 10)
    for number, (key, (x, y)) in enumerate(locations.items(), start=1):
        pdf.setFillColor(colors.HexColor('#1b447d') if key in state['path'] else colors.white)
        pdf.setStrokeColor(colors.HexColor('#1b447d'))
        pdf.circle(x, y, 9, stroke=1, fill=1)
        pdf.setFillColor(colors.white if key in state['path'] else colors.HexColor('#1b447d'))
        pdf.drawCentredString(x, y - 3, str(number))
    pdf.setFillColor(colors.HexColor('#173456'))
    numbers = {key: number for number, key in enumerate(points, start=1)}
    path = '  —  '.join(str(numbers[key]) for key in state['path'])
    pdf.drawString(48, 537, f'Путь от дома до школы: {path}')

    y = 503
    for key, destination in trail:
        node = points[key]
        if not node['decision']:
            continue
        if y < 155:
            pdf.showPage()
            pdf.setFont(font, 18)
            pdf.setFillColor(colors.HexColor('#173456'))
            pdf.drawString(48, 786, 'Безопасный маршрут · Разбор')
            y = 748
        option = next(option for option in node['choices'] if option['target'] == destination)
        pdf.setFont(font, 14)
        pdf.drawString(48, y, f"{numbers[key]}. {node['label']}")
        y -= 19
        pdf.setFont(font, 12)
        for line in simpleSplit(option['feedback'], font, 12, 499):
            pdf.drawString(48, y, line)
            y -= 16
        if node['rule']:
            pdf.drawString(48, y, node['rule'])
            pdf.linkURL(rule_url(node['rule']), (48, y - 3, 48 + pdf.stringWidth(node['rule'], font, 12), y + 12))
            y -= 17
        y -= 15

    pdf.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='safe-route.pdf', content_type='application/pdf')
