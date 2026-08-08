from django.contrib import admin

from .models import Enrollment, ImportError, ImportJob, Student

admin.site.register(Student)
admin.site.register(Enrollment)
admin.site.register(ImportJob)
admin.site.register(ImportError)
