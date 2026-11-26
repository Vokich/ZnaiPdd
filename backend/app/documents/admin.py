from django.contrib import admin

from app.models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'test_type', 'document_type', 'download_count', 'generated_at')
    list_filter = ('test_type', 'document_type', 'generated_at')
    search_fields = ('user__username', 'user__profile__surname1', 'user__profile__name')
    date_hierarchy = 'generated_at'
    readonly_fields = ('generated_at', 'download_count')
    list_per_page = 30
