from django.contrib import admin

from .models import (
    DevelopmentDimension,
    MatrixVersion,
    PedagogicalMatrix,
    Skill,
    SkillProgression,
    StatusLabelConfig,
)

admin.site.register(PedagogicalMatrix)
admin.site.register(MatrixVersion)
admin.site.register(DevelopmentDimension)
admin.site.register(Skill)
admin.site.register(SkillProgression)
admin.site.register(StatusLabelConfig)
