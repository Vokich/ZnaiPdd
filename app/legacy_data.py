from datetime import date

from django.db.models import Q


REPORT_PERMISSION = {
    'content_type__app_label': 'app',
    'content_type__model': 'teacherlessonreport',
    'codename': 'submit_lesson_reports',
}


def approved_teachers(users):
    direct = {'user_permissions__' + key: value for key, value in REPORT_PERMISSION.items()}
    through_group = {'groups__permissions__' + key: value for key, value in REPORT_PERMISSION.items()}
    return users.filter(Q(**direct) | Q(**through_group)).values_list('pk', flat=True)


def profile_updates(profile, username, municipality_codes):
    fields = {
        'role': 'teacher',
        'surname1': username,
        'name': '—',
        'surname2': '',
        'birth_date': date(1990, 1, 1),
        'school': '—',
        'region': '—',
        'position': '',
    }
    if all(profile[field] == value for field, value in fields.items()):
        return {'role': '', 'surname1': '', 'name': '', 'birth_date': None, 'school': '', 'region': ''}
    return {'municipality_id': municipality_codes.get(profile['region'])}
