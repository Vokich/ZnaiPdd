from datetime import date

from django.forms import DateField
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


def checked(form):
    errors = {}
    for name, field in form.fields.items():
        value = form.data.get(name)
        if isinstance(field, DateField) and value is not None and not isinstance(value, (date, str)):
            errors[name] = [field.error_messages['invalid']]
        elif isinstance(value, (dict, list)):
            errors[name] = ['Укажите одно значение.']
    if errors:
        raise ValidationError(errors)
    if not form.is_valid():
        raise ValidationError(form.errors)
    return form


def object_data(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'detail': 'Ожидается объект JSON.'})
    return request.data


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})
