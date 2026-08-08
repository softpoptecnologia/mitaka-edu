from django.contrib import admin

from .models import ClassroomIntervention, InterventionTemplate, StudentIntervention

admin.site.register(InterventionTemplate)
admin.site.register(StudentIntervention)
admin.site.register(ClassroomIntervention)
