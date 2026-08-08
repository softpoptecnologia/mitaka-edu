from django.contrib import admin

from .models import AggregatedIndicator, StudentSkillStatus

admin.site.register(StudentSkillStatus)
admin.site.register(AggregatedIndicator)
