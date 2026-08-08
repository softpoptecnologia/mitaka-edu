"""AccessibilityAssessmentResolver — keep adaptation logic out of views."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from apps.accessibility.models import AccessibilityFeature, StudentAccessibilityProfile
from apps.assessments.models import (
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentResponse,
    ItemAccessRequirement,
)


@dataclass
class ResolvedItem:
    item: AssessmentItem
    variant: AssessmentItemVariant | None
    source: str  # STANDARD | VARIANT
    equivalence: str  # STANDARD | EQUIVALENT | ALTERNATIVE | ...
    active_features: list[str] = field(default_factory=list)
    reason: str = ""
    counts_toward_score: bool = True
    prompt_text: str = ""
    prompt_image: object | None = None
    prompt_image_alt: str = ""
    prompt_audio: object | None = None
    item_type: str = ""
    requires_pedagogical_review: bool = False

    @property
    def display_prompt(self) -> str:
        return self.prompt_text or self.item.prompt


@dataclass
class ResolvedAssessment:
    student_id: int
    instrument_id: int
    active_features: list[str]
    items: list[ResolvedItem]
    standard_count: int = 0
    equivalent_count: int = 0
    alternative_count: int = 0
    blocked_count: int = 0
    not_applicable_count: int = 0

    def summary_dict(self) -> dict:
        return {
            "standard": self.standard_count,
            "equivalent": self.equivalent_count,
            "alternative": self.alternative_count,
            "blocked": self.blocked_count,
            "not_applicable": self.not_applicable_count,
            "active_features": self.active_features,
            "total_items": len(self.items),
        }


# Features that conflict with hard requirements on the standard item
CONFLICT_MAP: dict[str, set[str]] = {
    AccessibilityFeature.Code.VISUAL_SCREEN_READER: {
        ItemAccessRequirement.RequirementCode.REQUIRES_VISION,
        ItemAccessRequirement.RequirementCode.REQUIRES_COLOR_DISCRIMINATION,
    },
    AccessibilityFeature.Code.MOTOR_NO_DRAG: {
        ItemAccessRequirement.RequirementCode.REQUIRES_DRAG,
    },
    AccessibilityFeature.Code.MOTOR_KEYBOARD: {
        ItemAccessRequirement.RequirementCode.REQUIRES_DRAG,
        ItemAccessRequirement.RequirementCode.REQUIRES_MOTOR_PRECISION,
    },
    AccessibilityFeature.Code.COGNITIVE_NO_TIME_LIMIT: {
        ItemAccessRequirement.RequirementCode.REQUIRES_TIMED_RESPONSE,
    },
    AccessibilityFeature.Code.COGNITIVE_EXTRA_TIME: {
        ItemAccessRequirement.RequirementCode.REQUIRES_TIMED_RESPONSE,
    },
    AccessibilityFeature.Code.AUDITORY_CAPTIONS: {
        ItemAccessRequirement.RequirementCode.REQUIRES_AUDIO,
    },
    AccessibilityFeature.Code.AUDITORY_VISUAL_INSTRUCTION: {
        ItemAccessRequirement.RequirementCode.REQUIRES_AUDIO,
    },
    AccessibilityFeature.Code.AUDITORY_LIBRAS: {
        ItemAccessRequirement.RequirementCode.REQUIRES_AUDIO,
    },
}

# If these supports are missing on a vision-required item, screen reader users are blocked
SUPPORT_CODES = {
    ItemAccessRequirement.RequirementCode.SUPPORTS_SCREEN_READER,
    ItemAccessRequirement.RequirementCode.SUPPORTS_KEYBOARD,
}


class AccessibilityAssessmentResolver:
    """Resolve accessible presentation for a student + assessment item."""

    def student_feature_codes(self, student) -> list[str]:
        try:
            profile = student.accessibility_profile
        except StudentAccessibilityProfile.DoesNotExist:
            return []
        if not profile.is_active:
            return []
        return profile.active_feature_codes()

    def item_requirement_codes(self, item: AssessmentItem) -> set[str]:
        return set(
            item.access_requirements.filter(is_required=True).values_list("code", flat=True)
        )

    def item_support_codes(self, item: AssessmentItem) -> set[str]:
        return set(
            item.access_requirements.filter(is_required=False).values_list("code", flat=True)
        )

    def standard_is_accessible(self, item: AssessmentItem, feature_codes: Iterable[str]) -> tuple[bool, str]:
        features = set(feature_codes)
        hard = self.item_requirement_codes(item)
        supports = self.item_support_codes(item)

        for feature in features:
            conflicts = CONFLICT_MAP.get(feature, set())
            hit = hard & conflicts
            if hit:
                # Screen reader: allow if item explicitly supports screen reader and vision is only for media with alt path
                if feature == AccessibilityFeature.Code.VISUAL_SCREEN_READER:
                    if ItemAccessRequirement.RequirementCode.SUPPORTS_SCREEN_READER in supports:
                        # still block exclusive vision without textual prompt
                        if (
                            ItemAccessRequirement.RequirementCode.REQUIRES_VISION in hard
                            and not (item.prompt or "").strip()
                        ):
                            return False, "item_exclusively_visual"
                        continue
                    if ItemAccessRequirement.RequirementCode.REQUIRES_VISION in hard:
                        return False, "incompatible_vision"
                else:
                    return False, f"conflict:{','.join(sorted(hit))}"

        if AccessibilityFeature.Code.MOTOR_NO_DRAG in features and (
            ItemAccessRequirement.RequirementCode.REQUIRES_DRAG in hard
        ):
            return False, "requires_no_drag_alternative"

        return True, "ok"

    def _variant_compatible(self, variant: AssessmentItemVariant, feature_codes: set[str]) -> bool:
        if not variant.is_usable:
            return False
        supported = set(variant.supported_features.values_list("code", flat=True))
        # Variant must address at least one of the student's features when listed;
        # empty supported_features means generally accessible alternative.
        if supported and not (supported & feature_codes):
            # Still allow if it removes a conflict (e.g. NO_DRAG variant)
            if AccessibilityFeature.Code.MOTOR_NO_DRAG in feature_codes and (
                AccessibilityFeature.Code.MOTOR_NO_DRAG in supported
                or variant.item_type_override == AssessmentItem.ItemType.SELECT_THEN_MATCH
            ):
                return True
            return False
        # Variant's own hard requirements must not conflict
        var_hard = set(
            variant.access_requirements.filter(is_required=True).values_list("code", flat=True)
        )
        for feature in feature_codes:
            if var_hard & CONFLICT_MAP.get(feature, set()):
                return False
        return True

    def _usable_variants(self, item: AssessmentItem) -> list[AssessmentItemVariant]:
        return list(
            item.variants.filter(
                active=True,
                is_active=True,
                pedagogical_approval_status__in=[
                    AssessmentItemVariant.ApprovalStatus.APPROVED,
                    AssessmentItemVariant.ApprovalStatus.PUBLISHED,
                ],
            )
            .prefetch_related("supported_features", "access_requirements")
            .order_by("version", "id")
        )

    def resolve_item(self, *, student, assessment_item: AssessmentItem) -> ResolvedItem:
        features = self.student_feature_codes(student)
        feature_set = set(features)
        accessible, reason = self.standard_is_accessible(assessment_item, features)

        base_kwargs = dict(
            item=assessment_item,
            active_features=features,
            prompt_text=assessment_item.prompt,
            prompt_image=assessment_item.prompt_image,
            prompt_image_alt=assessment_item.prompt_image_alt or assessment_item.prompt[:120],
            prompt_audio=assessment_item.prompt_audio,
            item_type=assessment_item.item_type,
        )

        if accessible:
            return ResolvedItem(
                variant=None,
                source="STANDARD",
                equivalence=AssessmentResponse.EquivalenceApplied.STANDARD,
                reason=reason or "standard_ok",
                **base_kwargs,
            )

        variants = self._usable_variants(assessment_item)
        equivalent = [
            v
            for v in variants
            if v.equivalence_status == AssessmentItemVariant.EquivalenceStatus.EQUIVALENT
            and self._variant_compatible(v, feature_set)
        ]
        if equivalent:
            variant = equivalent[-1]  # prefer highest version (ordered)
            return self._from_variant(
                assessment_item,
                variant,
                features,
                AssessmentResponse.EquivalenceApplied.EQUIVALENT,
                "equivalent_variant",
            )

        alternative = [
            v
            for v in variants
            if v.equivalence_status == AssessmentItemVariant.EquivalenceStatus.ALTERNATIVE
            and self._variant_compatible(v, feature_set)
            and v.justification.strip()
        ]
        if alternative:
            variant = alternative[-1]
            return self._from_variant(
                assessment_item,
                variant,
                features,
                AssessmentResponse.EquivalenceApplied.ALTERNATIVE,
                "alternative_variant",
            )

        # No usable variant — never auto-mark as wrong
        return ResolvedItem(
            variant=None,
            source="BLOCKED",
            equivalence=AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
            reason="requires_alternative_instrument",
            counts_toward_score=False,
            requires_pedagogical_review=True,
            **base_kwargs,
        )

    def _from_variant(
        self,
        item: AssessmentItem,
        variant: AssessmentItemVariant,
        features: list[str],
        equivalence: str,
        reason: str,
    ) -> ResolvedItem:
        return ResolvedItem(
            item=item,
            variant=variant,
            source="VARIANT",
            equivalence=equivalence,
            active_features=features,
            reason=reason,
            counts_toward_score=True,
            prompt_text=variant.instruction_text or item.prompt,
            prompt_image=variant.instruction_image or item.prompt_image,
            prompt_image_alt=variant.instruction_image_alt or item.prompt_image_alt or item.prompt[:120],
            prompt_audio=variant.instruction_audio or item.prompt_audio,
            item_type=variant.item_type_override or item.item_type,
            requires_pedagogical_review=(
                equivalence == AssessmentResponse.EquivalenceApplied.ALTERNATIVE
            ),
        )

    def resolve_instrument(self, *, student, instrument) -> ResolvedAssessment:
        features = self.student_feature_codes(student)
        items = list(instrument.items.prefetch_related("access_requirements", "variants").order_by("order", "id"))
        resolved: list[ResolvedItem] = []
        counts = {
            "standard": 0,
            "equivalent": 0,
            "alternative": 0,
            "blocked": 0,
            "not_applicable": 0,
        }
        for item in items:
            r = self.resolve_item(student=student, assessment_item=item)
            resolved.append(r)
            if r.equivalence == AssessmentResponse.EquivalenceApplied.STANDARD:
                counts["standard"] += 1
            elif r.equivalence == AssessmentResponse.EquivalenceApplied.EQUIVALENT:
                counts["equivalent"] += 1
            elif r.equivalence == AssessmentResponse.EquivalenceApplied.ALTERNATIVE:
                counts["alternative"] += 1
            elif r.equivalence in {
                AssessmentResponse.EquivalenceApplied.REQUIRES_ALTERNATIVE,
                AssessmentResponse.EquivalenceApplied.BLOCKED,
            }:
                counts["blocked"] += 1
            elif r.equivalence == AssessmentResponse.EquivalenceApplied.NOT_APPLICABLE:
                counts["not_applicable"] += 1

        return ResolvedAssessment(
            student_id=student.pk,
            instrument_id=instrument.pk,
            active_features=features,
            items=resolved,
            standard_count=counts["standard"],
            equivalent_count=counts["equivalent"],
            alternative_count=counts["alternative"],
            blocked_count=counts["blocked"],
            not_applicable_count=counts["not_applicable"],
        )


def css_classes_for_features(feature_codes: Iterable[str]) -> list[str]:
    classes = list(
        AccessibilityFeature.objects.filter(code__in=list(feature_codes), is_active=True)
        .exclude(css_class="")
        .values_list("css_class", flat=True)
    )
    # Always honor system reduced-motion via CSS media query; feature adds class too
    return classes
