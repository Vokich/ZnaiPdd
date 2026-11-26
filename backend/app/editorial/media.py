from io import BytesIO
from mimetypes import guess_type
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, Http404
from PIL import Image, ImageOps


def prepare_image(upload, *, keep_transparency=False):
    if not isinstance(upload, UploadedFile):
        return upload
    if upload.size > 8 * 1024 * 1024:
        raise ValidationError('Размер изображения должен быть не больше 8 МБ.')
    try:
        with Image.open(upload) as source:
            if source.width * source.height > 24_000_000:
                raise ValidationError('Уменьшите разрешение изображения.')
            fitted = ImageOps.exif_transpose(source).convert('RGBA')
            fitted.thumbnail((1600, 1200))
            transparent = keep_transparency and fitted.getextrema()[-1][0] < 255
            image = Image.new('RGBA' if transparent else 'RGB', fitted.size, 'white')
            if transparent:
                image.paste(fitted)
            else:
                image.paste(fitted, mask=fitted.getchannel('A'))
            buffer = BytesIO()
            image.save(buffer, format='PNG' if transparent else 'JPEG', quality=88, optimize=True)
    except (OSError, Image.DecompressionBombError) as error:
        raise ValidationError('Не удалось обработать изображение.') from error
    extension = 'png' if transparent else 'jpg'
    return ContentFile(buffer.getvalue(), name=f'{uuid4().hex}.{extension}')


def gallery_data(images):
    return [{'id': item.pk, 'url': item.image.url, 'alt': item.alt, 'caption': item.caption} for item in images]


def image_response(image):
    content_type = guess_type(image.name)[0]
    if not content_type or not content_type.startswith('image/') or content_type == 'image/svg+xml':
        raise Http404
    try:
        stream = image.open('rb')
    except FileNotFoundError as error:
        raise Http404 from error
    response = FileResponse(stream, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    return response
