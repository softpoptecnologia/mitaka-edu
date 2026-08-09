from django.contrib import admin

from apps.adoption.models import FormationProgram


@admin.register(FormationProgram)
class FormationProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "modality", "duration_hours", "is_active")
    list_filter = ("audience", "modality", "is_active")
    search_fields = ("title", "objective")
