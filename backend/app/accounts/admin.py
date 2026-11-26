from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, User

from app.accounts.access import ADMIN, account_role
from app.models import Organization, Profile, TeacherContact


@admin.register(TeacherContact)
class TeacherContactAdmin(admin.ModelAdmin):
    list_display = ('label', 'url', 'direct')


ACCOUNT_ROLES = {**dict(Profile.Role.choices), ADMIN: 'Администратор'}


class AccountFields(forms.ModelForm):
    organization = forms.ModelChoiceField(label='Организация', queryset=Organization.objects.select_related('municipality'),
        required=False, widget=AutocompleteSelect(Profile._meta.get_field('organization'), admin.site))
    organization_confirmed = forms.BooleanField(label='Принадлежность подтверждена по личному обращению', required=False)
    account_role = forms.ChoiceField(label='Профиль доступа', choices=ACCOUNT_ROLES.items())
    surname1 = forms.CharField(label='Фамилия', max_length=50, required=False)
    name = forms.CharField(label='Имя', max_length=50, required=False)
    surname2 = forms.CharField(label='Отчество', max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        self.initial['account_role'] = account_role(self.instance) or Profile.Role.CHILD
        if profile:
            self.initial.update(organization=profile.organization_id, organization_confirmed=profile.organization_confirmed)
            for field in ('surname1', 'name', 'surname2'):
                self.initial[field] = getattr(profile, field)


class AccountChangeForm(AccountFields, UserChangeForm):
    pass


class AccountCreationForm(AccountFields, AdminUserCreationForm):
    pass


class UserAdmin(BaseUserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    list_display = ('username', 'email', 'get_full_name', 'account_role', 'is_active')
    list_filter = ('is_active',)
    list_select_related = ('profile',)
    search_fields = ('username', 'email', 'profile__surname1', 'profile__name', 'profile__school')
    ordering = ('-date_joined',)
    personal_fields = ('surname1', 'name', 'surname2', 'email', 'organization', 'organization_confirmed')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'account_role', 'is_active')}),
        ('Личные данные', {'fields': personal_fields}),
    )
    add_fieldsets = (
        (None, {'fields': ('username', 'usable_password', 'password1', 'password2', 'account_role')}),
        ('Личные данные', {'fields': personal_fields}),
    )

    @admin.display(description='ФИО')
    def get_full_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.full_name if profile else '—'

    @admin.display(description='Профиль доступа')
    def account_role(self, obj):
        return ACCOUNT_ROLES.get(account_role(obj), 'Нужно завершить настройку')

    def get_readonly_fields(self, request, obj=None):
        return ('account_role', 'is_active') if obj and request.user.pk == obj.pk else ()

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and (obj is None or request.user.pk != obj.pk)

    def save_model(self, request, obj, form, change):
        role = form.cleaned_data.get('account_role', account_role(obj))
        obj.is_staff = obj.is_superuser = role == ADMIN
        super().save_model(request, obj, form, change)
        fields = {field: form.cleaned_data[field] for field in ('surname1', 'name', 'surname2')}
        fields['role'] = Profile.Role.CHILD if role == ADMIN else role
        fields['organization'] = form.cleaned_data['organization']
        fields['organization_confirmed'] = bool(fields['organization'] and form.cleaned_data['organization_confirmed'])
        Profile.objects.update_or_create(user=obj, defaults=fields)


admin.site.unregister(Group)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
