from django.db import transaction

from app.models import PlatformAttempt, TestResult


def answer_row(question, selected, expected, correct):
    return dict(question=question, selected=selected, expected=expected, correct=bool(correct))


def record(user, kind, task, title, answers, *, version='', score=None, total=None, source=None):
    account = user if user and user.is_authenticated else None
    profile = getattr(account, 'profile', None)
    organization = profile.organization if profile and profile.organization_confirmed else None
    values = dict(kind=kind, task=str(task), title=title, version=str(version), user=account,
                  organization=organization.name if organization else '', answers=answers,
                  score=sum(row['correct'] for row in answers) if score is None else score,
                  total=len(answers) if total is None else total)
    if source is None:
        return PlatformAttempt.objects.create(**values)
    attempt, created = PlatformAttempt.objects.get_or_create(source=source, defaults=values)
    if not created and account and attempt.user_id is None and kind == PlatformAttempt.Kind.ROUTE:
        PlatformAttempt.objects.filter(pk=attempt.pk, user__isnull=True).update(
            user=account, organization=values['organization'])
    return attempt


@transaction.atomic
def save_age_result(user, form):
    checked = form.check_answers()
    result = TestResult.objects.create(user=user, test_type=form.test_type, score=checked['score'],
                                       total_questions=checked['total'], passing_score=checked['passing_score'],
                                       passed=checked['passed'])
    rows = []
    for question in form.questions_data:
        value = checked['results'][question['id']]
        options = question['options']
        rows.append(answer_row(question['text'], options[value['user_answer'] - 1],
                               options[question['correct'] - 1], value['is_correct']))
    record(user, 'age', form.test_type, result.get_test_type_display(), rows,
           version=form.revision, source=f'age:{result.pk}')
    return result


@transaction.atomic
def save_sign_answer(user, sign, answer):
    from app.signs.catalog import mark_sign_learned
    options = sign.answer_options
    record(user, 'sign', sign.pk, sign.name, [answer_row(
        sign.question, options[answer - 1], options[sign.correct_answer - 1], answer == sign.correct_answer)])
    if answer == sign.correct_answer:
        mark_sign_learned(user, sign)
        return True
    return False


def practice_answers(version, answer, correct):
    data = version.content
    if version.kind == 'order':
        def labels(order):
            return ' → '.join(data['cards'][value - 1] for value in order)
        return [answer_row(version.prompt, labels(answer), ' / '.join(map(labels, data['orders'])), correct)]
    rows = []
    for label, index, options, allowed in (
        ('Значение знака', answer[0], data['meanings'], data['right_meanings']),
        (version.plate_a.name, answer[1], data['conditions'], data['right_a']),
        (version.plate_b.name, answer[2], data['conditions'], data['right_b']),
    ):
        rows.append(answer_row(f'{version.prompt} · {label}', options[index - 1],
                               ' / '.join(options[i - 1] for i in allowed), index in allowed))
    return rows
