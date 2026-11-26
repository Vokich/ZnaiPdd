from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view


@api_view(['GET'])
def training_material(request):
    path = settings.BASE_DIR / 'app' / 'static' / 'images' / 'академия ворд (2).docx'
    try:
        document = path.open('rb')
    except FileNotFoundError:
        raise Http404('Методический материал не найден.')
    return FileResponse(
        document,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename='академия_ворд.docx',
    )
