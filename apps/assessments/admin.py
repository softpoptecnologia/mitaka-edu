from django.contrib import admin

from .models import (
    AssessmentInstrument,
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentOption,
    AssessmentResponse,
    AssessmentSession,
    ItemAccessRequirement,
    ScoringRule,
    SessionSkillResult,
    SkillResultMapping,
    VariantAccessRequirement,
)


class AssessmentOptionInline(admin.TabularInline):
    model = AssessmentOption
    extra = 0


class ItemAccessRequirementInline(admin.TabularInline):
    model = ItemAccessRequirement
    extra = 0


class AssessmentItemVariantInline(admin.TabularInline):
    model = AssessmentItemVariant
    extra = 0
    fields = (
        "name",
        "version",
        "equivalence_status",
        "adaptation_type",
        "pedagogical_approval_status",
        "active",
    )


@admin.register(AssessmentItem)
class AssessmentItemAdmin(admin.ModelAdmin):
    list_display = ("instrument", "order", "code", "item_type")
    inlines = [AssessmentOptionInline, ItemAccessRequirementInline, AssessmentItemVariantInline]


class VariantAccessRequirementInline(admin.TabularInline):
    model = VariantAccessRequirement
    extra = 0


@admin.register(AssessmentItemVariant)
class AssessmentItemVariantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "parent_item",
        "version",
        "equivalence_status",
        "adaptation_type",
        "pedagogical_approval_status",
        "active",
    )
    list_filter = ("equivalence_status", "pedagogical_approval_status", "adaptation_type")
    filter_horizontal = ("supported_features",)
    inlines = [VariantAccessRequirementInline]


admin.site.register(AssessmentInstrument)
admin.site.register(AssessmentOption)
admin.site.register(AssessmentSession)
admin.site.register(AssessmentResponse)
admin.site.register(SessionSkillResult)
admin.site.register(ScoringRule)
admin.site.register(SkillResultMapping)
admin.site.register(ItemAccessRequirement)
