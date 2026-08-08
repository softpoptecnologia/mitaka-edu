from django.contrib import admin

from apps.accessibility.models import (
    AccessibilityCategory,
    AccessibilityFeature,
    StudentAccessibilityFeature,
    StudentAccessibilityProfile,
    StudentSupportPlan,
    StudentSupportStrategy,
)


@admin.register(AccessibilityCategory)
class AccessibilityCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "order")


@admin.register(AccessibilityFeature)
class AccessibilityFeatureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "css_class", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name")


class StudentAccessibilityFeatureInline(admin.TabularInline):
    model = StudentAccessibilityFeature
    extra = 0


@admin.register(StudentAccessibilityProfile)
class StudentAccessibilityProfileAdmin(admin.ModelAdmin):
    list_display = ("student", "is_active", "updated_at")
    search_fields = ("student__full_name", "student__external_code")
    inlines = [StudentAccessibilityFeatureInline]


class StudentSupportStrategyInline(admin.TabularInline):
    model = StudentSupportStrategy
    extra = 0


@admin.register(StudentSupportPlan)
class StudentSupportPlanAdmin(admin.ModelAdmin):
    list_display = ("student", "school_year", "status", "start_date")
    list_filter = ("status", "school_year")
    filter_horizontal = ("responsible_users",)
    inlines = [StudentSupportStrategyInline]
