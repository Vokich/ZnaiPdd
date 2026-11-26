from django.contrib import admin

from app.models import Municipality, Organization


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('name', 'code')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality')
    list_select_related = ('municipality',)
    search_fields = ('name', 'municipality__name')
    autocomplete_fields = ('municipality',)
