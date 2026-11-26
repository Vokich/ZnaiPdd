from django.contrib import admin

from app.models import (
    ClassroomAttempt, ClassroomQuiz, ClassroomRun, ClassroomVersion,
    NewsImage, PracticeImage, PracticeResult, Profile, RouteProgress,
)


class PlatformDataAdmin(admin.ModelAdmin):
    """Administrative access to records maintained by the platform's API."""

    list_per_page = 50

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


for model in (
    ClassroomAttempt, ClassroomQuiz, ClassroomRun, ClassroomVersion,
    NewsImage, PracticeImage, PracticeResult, Profile, RouteProgress,
):
    admin.site.register(model, PlatformDataAdmin)
