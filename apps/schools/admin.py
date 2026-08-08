from django.contrib import admin

from .models import Classroom, Municipality, School, SchoolYear, TeacherClassroom

admin.site.register(Municipality)
admin.site.register(School)
admin.site.register(SchoolYear)
admin.site.register(Classroom)
admin.site.register(TeacherClassroom)
