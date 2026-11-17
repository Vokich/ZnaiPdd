from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import DatabaseError, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import F

from app.legacy_data import REPORT_PERMISSION, approved_teachers, profile_updates
from app.models import Certificate, Municipality, Profile, RoadSign, TeacherLessonReport, TestResult, UserSignProgress


SOURCE = 'legacy_sqlite'
TARGET = 'default'
LEGACY_MIGRATION = ('app', '0008_alter_profile_role_alter_roadsign_category')
MODELS = (Group, User, Profile, RoadSign, TestResult, Certificate, TeacherLessonReport, UserSignProgress)
MEMBERSHIPS = (Group.permissions, User.groups, User.user_permissions)


class Command(BaseCommand):
    help = 'Copy retained records from a private SQLite backup into an empty, migrated database.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('source', type=Path, help='Path to a consistent SQLite backup.')
        parser.add_argument('--dry-run', action='store_true', help='Verify the transfer, then roll back.')

    def handle(self, source, dry_run, **options):
        source = source.resolve(strict=True) if source.is_file() else source
        if not source.is_file():
            raise CommandError('SQLite backup does not exist.')
        if source == (settings.BASE_DIR / 'db.sqlite3').resolve():
            raise CommandError('Use a private backup stored outside the project checkout.')

        target = connections[TARGET]
        if target.vendor == 'sqlite' and source == Path(target.settings_dict['NAME']).resolve():
            raise CommandError('Source and destination must be different databases.')
        connections.databases[SOURCE] = {
            **target.settings_dict,
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': source.as_uri() + '?mode=ro',
            'OPTIONS': {'uri': True},
            'CONN_MAX_AGE': 0,
        }
        try:
            with transaction.atomic(using=SOURCE), transaction.atomic(using=TARGET):
                counts = self.copy_database(target, dry_run)
        except DatabaseError:
            raise CommandError('Database error during transfer. No imported rows were committed. Check the backup and the target schema.') from None
        finally:
            connections[SOURCE].close()

        for name, count in counts.items():
            self.stdout.write(f'{name}: {count}')
        self.stdout.write(self.style.SUCCESS('Dry run verified and rolled back.' if dry_run else 'Transfer verified and committed.'))

    def copy_database(self, target, dry_run):
        loader = MigrationExecutor(connections[SOURCE]).loader
        applied = {key for key in loader.applied_migrations if key[0] == 'app'}
        if LEGACY_MIGRATION not in applied or ('app', '0009_normalize_profiles_and_reports') in applied:
            raise CommandError('Expected the legacy app schema at migration 0008.')
        if any(model.objects.using(TARGET).exists() for model in MODELS):
            raise CommandError('The target already contains application records. Start with an empty migrated database.')

        legacy = loader.project_state([LEGACY_MIGRATION]).apps
        old_certificates = legacy.get_model('app', 'Certificate').objects.using(SOURCE)
        if old_certificates.exclude(test_result__user_id=F('user_id'), test_result__test_type=F('test_type')).exists():
            raise CommandError('The backup contains documents linked to a result from another account or test type.')

        codes = dict(Municipality.objects.using(TARGET).values_list('name', 'pk'))
        users = User.objects.using(SOURCE)
        usernames = dict(users.values_list('pk', 'username'))
        teachers = set(approved_teachers(users))
        counts = {}
        for model in MODELS:
            source_model = legacy.get_model('app', model.__name__) if model._meta.app_label == 'app' else model
            rows = self.copy_rows(model, source_model, codes, usernames, teachers)
            counts[model._meta.label] = rows

        permission_ids = self.permission_ids()
        for membership in MEMBERSHIPS:
            through = membership.through
            counts[through._meta.label] = self.copy_memberships(through, permission_ids)
        target.check_constraints()
        if dry_run:
            transaction.set_rollback(True, using=TARGET)
        else:
            with target.cursor() as cursor:
                for sql in target.ops.sequence_reset_sql(no_style(), MODELS):
                    cursor.execute(sql)
        return counts

    def copy_rows(self, model, source_model, codes, usernames, teachers):
        source_fields = [field.attname for field in source_model._meta.concrete_fields]
        if model is TeacherLessonReport:
            source_fields.remove('children_list')
            source_fields.remove('photo_link')
        source = source_model.objects.using(SOURCE).order_by('pk')
        target = model.objects.using(TARGET).order_by('pk')
        batch_size = 500
        last_pk = None
        count = 0
        while True:
            batch = source if last_pk is None else source.filter(pk__gt=last_pk)
            rows = list(batch.values(*source_fields)[:batch_size])
            if not rows:
                break
            for values in rows:
                if model is Profile:
                    values.update(profile_updates(values, usernames[values['user_id']], codes))
                    if values['role'] == 'teacher' and values['user_id'] not in teachers:
                        values['role'] = 'child'
                if model is User and not values['is_superuser']:
                    values['is_staff'] = False
                if model is TeacherLessonReport:
                    values['participants_count'] = values.pop('children_count')
                model(**values).save_base(raw=True, force_insert=True, using=TARGET)
            ids = [values['id'] for values in rows]
            copied = list(target.filter(pk__in=ids).values())
            if len(copied) != len(rows) or any(
                {field: row[field] for field in expected} != expected for row, expected in zip(copied, rows)
            ):
                raise CommandError(f'Row verification failed for {model._meta.label}.')
            last_pk = ids[-1]
            count += len(rows)
        if target.count() != count:
            raise CommandError(f'Count verification failed for {model._meta.label}.')
        return count

    def permission_ids(self):
        fields = ('id', 'content_type__app_label', 'content_type__model', 'codename')
        current = {
            (app, model, code): pk
            for pk, app, model, code in Permission.objects.using(TARGET).values_list(*fields)
        }
        return {
            pk: current.get((app, model, code))
            for pk, app, model, code in Permission.objects.using(SOURCE).values_list(*fields)
        }

    def copy_memberships(self, through, permission_ids):
        fields = [field.attname for field in through._meta.concrete_fields if not field.primary_key]
        manager = through.objects.using(TARGET)
        source = through.objects.using(SOURCE)
        if 'permission_id' in fields:
            source = source.exclude(**{'permission__' + key: value for key, value in REPORT_PERMISSION.items()})
        rows = list(source.values(*fields))
        for row in rows:
            if 'permission_id' in row:
                mapped = permission_ids[row['permission_id']]
                if mapped is None:
                    raise CommandError('The backup contains an assigned permission absent from the new schema.')
                row['permission_id'] = mapped
        manager.bulk_create(through(**row) for row in rows)
        if set(manager.values_list(*fields)) != {tuple(row[field] for field in fields) for row in rows}:
            raise CommandError(f'Membership verification failed for {through._meta.label}.')
        return len(rows)
