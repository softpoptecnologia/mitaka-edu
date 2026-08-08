"""Assessment instruments, sessions, responses and accessible variants."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SoftDeleteModel, TimeStampedModel


class AssessmentInstrument(TimeStampedModel, SoftDeleteModel):
    class InstrumentType(models.TextChoices):
        DIGITAL = "digital", "Digital / Gamificada"
        OBSERVATIONAL = "observational", "Observacional"

    matrix_version = models.ForeignKey(
        "curriculum.MatrixVersion",
        on_delete=models.PROTECT,
        related_name="instruments",
    )
    skill = models.ForeignKey(
        "curriculum.Skill",
        on_delete=models.PROTECT,
        related_name="instruments",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instrument_type = models.CharField(max_length=20, choices=InstrumentType.choices)
    estimated_minutes = models.PositiveIntegerField(default=10)
    is_published = models.BooleanField(default=True)
    # When True, response time is part of the pedagogical construct (rare).
    time_is_construct = models.BooleanField(
        default=False,
        help_text="Se verdadeiro, tempo faz parte da habilidade avaliada. Caso contrário, tempo é só metadado.",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class AssessmentItem(TimeStampedModel):
    class ItemType(models.TextChoices):
        IMAGE_SELECT = "image_select", "Imagem → selecionar imagem"
        AUDIO_IMAGE = "audio_image", "Áudio/texto → selecionar imagem"
        IMAGE_CHOICE = "image_choice", "Imagem → selecionar alternativa"
        SINGLE_SELECT = "single_select", "Seleção simples"
        VISUAL_TF = "visual_tf", "Verdadeiro/Falso visual"
        OBSERVATION_SCALE = "observation_scale", "Escala observacional"
        # Accessible alternative to drag-and-drop association
        SELECT_THEN_MATCH = "select_then_match", "Selecionar e associar (sem arrastar)"

    instrument = models.ForeignKey(AssessmentInstrument, on_delete=models.CASCADE, related_name="items")
    order = models.PositiveIntegerField(default=0)
    item_type = models.CharField(max_length=30, choices=ItemType.choices)
    prompt = models.TextField()
    prompt_audio = models.FileField(upload_to="assessments/audio/", blank=True, null=True)
    prompt_image = models.ImageField(upload_to="assessments/images/", blank=True, null=True)
    prompt_image_alt = models.CharField(max_length=255, blank=True)
    help_text = models.CharField(max_length=255, blank=True)
    code = models.CharField(max_length=40, blank=True, help_text="Código estável para biblioteca (ex.: RIM-001)")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.instrument.title} #{self.order}"


class ItemAccessRequirement(TimeStampedModel):
    """Functional requirements of an item — prefer table over rigid BooleanFields."""

    class RequirementCode(models.TextChoices):
        REQUIRES_VISION = "requires_vision", "Requer visão"
        REQUIRES_AUDIO = "requires_audio", "Requer áudio"
        REQUIRES_MOTOR_PRECISION = "requires_motor_precision", "Requer precisão motora"
        REQUIRES_DRAG = "requires_drag", "Requer arrastar e soltar"
        REQUIRES_READING = "requires_reading", "Requer leitura"
        REQUIRES_COLOR_DISCRIMINATION = "requires_color_discrimination", "Requer discriminação de cores"
        REQUIRES_TIMED_RESPONSE = "requires_timed_response", "Requer resposta cronometrada"
        SUPPORTS_SCREEN_READER = "supports_screen_reader", "Compatível com leitor de tela"
        SUPPORTS_KEYBOARD = "supports_keyboard", "Compatível com teclado"

    item = models.ForeignKey(AssessmentItem, on_delete=models.CASCADE, related_name="access_requirements")
    code = models.CharField(max_length=64, choices=RequirementCode.choices)
    is_required = models.BooleanField(
        default=True,
        help_text="False = capability/support flag (supports_*); True = hard requirement.",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("item", "code")]
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.item_id}:{self.code}"


class AssessmentOption(TimeStampedModel):
    item = models.ForeignKey(AssessmentItem, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=200)
    image = models.ImageField(upload_to="assessments/options/", blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    score_value = models.IntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.label


class AssessmentItemVariant(TimeStampedModel, SoftDeleteModel):
    """Accessible or alternative presentation of a canonical AssessmentItem."""

    class EquivalenceStatus(models.TextChoices):
        EQUIVALENT = "EQUIVALENT", "Equivalente (acomodação de acesso)"
        ALTERNATIVE = "ALTERNATIVE", "Alternativo (revisão pedagógica)"
        NOT_EQUIVALENT = "NOT_EQUIVALENT", "Não equivalente"

    class ApprovalStatus(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        SUBMITTED = "SUBMITTED", "Enviado"
        PEDAGOGICAL_REVIEW = "PEDAGOGICAL_REVIEW", "Revisão pedagógica"
        APPROVED = "APPROVED", "Aprovado"
        PUBLISHED = "PUBLISHED", "Publicado"
        ARCHIVED = "ARCHIVED", "Arquivado"

    class AdaptationType(models.TextChoices):
        ACCESS_ACCOMMODATION = "ACCESS_ACCOMMODATION", "Acomodação de acesso"
        PEDAGOGICAL_MODIFICATION = "PEDAGOGICAL_MODIFICATION", "Modificação pedagógica"

    parent_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=120)
    instruction_text = models.TextField(blank=True)
    instruction_audio = models.FileField(upload_to="assessments/variants/audio/", blank=True, null=True)
    instruction_image = models.ImageField(upload_to="assessments/variants/images/", blank=True, null=True)
    instruction_image_alt = models.CharField(max_length=255, blank=True)
    instruction_video = models.FileField(upload_to="assessments/variants/video/", blank=True, null=True)
    instruction_libras_video = models.FileField(upload_to="assessments/variants/libras/", blank=True, null=True)
    item_type_override = models.CharField(
        max_length=30,
        blank=True,
        choices=AssessmentItem.ItemType.choices,
        help_text="Se preenchido, altera o modo de interação sem mudar o item canônico.",
    )
    equivalence_status = models.CharField(max_length=20, choices=EquivalenceStatus.choices)
    equivalence_notes = models.TextField(blank=True)
    adaptation_type = models.CharField(
        max_length=40,
        choices=AdaptationType.choices,
        default=AdaptationType.ACCESS_ACCOMMODATION,
    )
    pedagogical_approval_status = models.CharField(
        max_length=30,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
    )
    justification = models.TextField(
        blank=True,
        help_text="Obrigatório para modificação pedagógica.",
    )
    support_plan = models.ForeignKey(
        "accessibility.StudentSupportPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="item_variants",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_item_variants",
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposed_item_variants",
    )
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    supported_features = models.ManyToManyField(
        "accessibility.AccessibilityFeature",
        blank=True,
        related_name="supported_variants",
    )

    class Meta:
        ordering = ["parent_item_id", "name", "version"]
        unique_together = [("parent_item", "name", "version")]

    def __str__(self) -> str:
        return f"{self.parent_item} / {self.name} v{self.version}"

    def clean(self):
        if self.adaptation_type == self.AdaptationType.PEDAGOGICAL_MODIFICATION and not self.justification.strip():
            raise ValidationError(
                {"justification": "Modificação pedagógica exige justificativa explícita."}
            )
        if (
            self.equivalence_status in {self.EquivalenceStatus.ALTERNATIVE, self.EquivalenceStatus.NOT_EQUIVALENT}
            and self.adaptation_type == self.AdaptationType.ACCESS_ACCOMMODATION
            and not self.justification.strip()
        ):
            # Soft guidance: alternative should not be silent
            pass

    @property
    def is_usable(self) -> bool:
        return (
            self.active
            and self.is_active
            and self.pedagogical_approval_status
            in {
                self.ApprovalStatus.APPROVED,
                self.ApprovalStatus.PUBLISHED,
            }
        )


class VariantAccessRequirement(TimeStampedModel):
    variant = models.ForeignKey(
        AssessmentItemVariant,
        on_delete=models.CASCADE,
        related_name="access_requirements",
    )
    code = models.CharField(max_length=64, choices=ItemAccessRequirement.RequirementCode.choices)
    is_required = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("variant", "code")]


class AssessmentSession(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Em andamento"
        COMPLETED = "completed", "Concluída"
        PARTIALLY_COMPLETED = "partially_completed", "Parcialmente concluída"
        NOT_APPLICABLE = "not_applicable", "Não aplicável"
        REQUIRES_ALTERNATIVE_INSTRUMENT = (
            "requires_alternative_instrument",
            "Requer instrumento alternativo",
        )
        ACCESSIBILITY_BLOCKED = "accessibility_blocked", "Bloqueada por acessibilidade"
        ABANDONED = "abandoned", "Abandonada"

    class ApplicationMode(models.TextChoices):
        STANDARD = "standard", "Padrão"
        ADAPTED = "adapted", "Adaptada"
        OBSERVATIONAL = "observational", "Observacional"

    enrollment = models.ForeignKey(
        "students.Enrollment",
        on_delete=models.PROTECT,
        related_name="assessment_sessions",
    )
    instrument = models.ForeignKey(AssessmentInstrument, on_delete=models.PROTECT, related_name="sessions")
    matrix_version = models.ForeignKey(
        "curriculum.MatrixVersion",
        on_delete=models.PROTECT,
        related_name="assessment_sessions",
        help_text="Versão congelada no início da sessão",
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_sessions",
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_item_order = models.PositiveIntegerField(default=0)
    application_mode = models.CharField(
        max_length=20,
        choices=ApplicationMode.choices,
        default=ApplicationMode.STANDARD,
    )
    active_features = models.JSONField(
        default=list,
        blank=True,
        help_text="Códigos de recursos de acessibilidade ativos na sessão (snapshot).",
    )
    adaptation_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Resumo imutável da montagem adaptativa (contagens e decisões).",
    )
    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Metadado de tempo; não reduz pontuação automaticamente.",
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Sessão {self.pk} — {self.enrollment.student}"

    @property
    def student(self):
        return self.enrollment.student


class AssessmentResponse(TimeStampedModel):
    class EquivalenceApplied(models.TextChoices):
        STANDARD = "STANDARD", "Padrão"
        EQUIVALENT = "EQUIVALENT", "Equivalente"
        ALTERNATIVE = "ALTERNATIVE", "Alternativo"
        NOT_APPLICABLE = "NOT_APPLICABLE", "Não aplicável"
        BLOCKED = "BLOCKED", "Bloqueado por acessibilidade"
        REQUIRES_ALTERNATIVE = "REQUIRES_ALTERNATIVE", "Requer instrumento alternativo"
        REQUIRES_PEDAGOGICAL_REVIEW = "REQUIRES_PEDAGOGICAL_REVIEW", "Requer revisão pedagógica"

    session = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name="responses")
    item = models.ForeignKey(AssessmentItem, on_delete=models.PROTECT, related_name="responses")
    option = models.ForeignKey(
        AssessmentOption,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="responses",
    )
    text_value = models.TextField(blank=True)
    score_value = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now=True)
    # Accessibility / adaptation audit trail (immutable snapshot for history)
    original_item = models.ForeignKey(
        AssessmentItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="original_responses",
    )
    variant_used = models.ForeignKey(
        AssessmentItemVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="responses",
    )
    variant_version = models.PositiveIntegerField(null=True, blank=True)
    variant_name_snapshot = models.CharField(max_length=120, blank=True)
    equivalence_applied = models.CharField(
        max_length=40,
        choices=EquivalenceApplied.choices,
        default=EquivalenceApplied.STANDARD,
    )
    active_features_snapshot = models.JSONField(default=list, blank=True)
    is_observational = models.BooleanField(default=False)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_responses",
    )
    counts_toward_score = models.BooleanField(
        default=True,
        help_text="False para NOT_APPLICABLE / BLOCKED — barreira ≠ baixo desempenho.",
    )
    response_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    instruction_repeats = models.PositiveIntegerField(
        default=0,
        help_text="Repetições de instrução; não reduz pontuação automaticamente.",
    )

    class Meta:
        unique_together = [("session", "item")]
        ordering = ["item__order"]

    def __str__(self) -> str:
        return f"Resp {self.session_id}/{self.item_id}"


class SessionSkillResult(TimeStampedModel):
    session = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name="skill_results")
    skill = models.ForeignKey("curriculum.Skill", on_delete=models.PROTECT, related_name="session_results")
    raw_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)
    result_code = models.CharField(max_length=50, blank=True)
    status_code = models.CharField(max_length=50)
    status_label = models.CharField(max_length=100)
    needs_attention = models.BooleanField(default=False)
    recommended_template = models.ForeignKey(
        "interventions.InterventionTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    accessibility_note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Ex.: versão acessível utilizada; não implica redução de expectativa.",
    )

    class Meta:
        unique_together = [("session", "skill")]

    def __str__(self) -> str:
        return f"{self.skill}: {self.status_label}"


class ScoringRule(TimeStampedModel):
    """Configurable score bands — criteria live in DB, not hardcoded in Python."""

    instrument = models.ForeignKey(AssessmentInstrument, on_delete=models.CASCADE, related_name="scoring_rules")
    skill = models.ForeignKey("curriculum.Skill", on_delete=models.CASCADE, related_name="scoring_rules")
    min_score = models.IntegerField()
    max_score = models.IntegerField()
    result_code = models.CharField(max_length=50)
    status_code = models.CharField(max_length=50)
    label = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["min_score"]

    def __str__(self) -> str:
        return f"{self.skill}: {self.min_score}-{self.max_score} → {self.status_code}"


class SkillResultMapping(TimeStampedModel):
    scoring_rule = models.ForeignKey(ScoringRule, on_delete=models.CASCADE, related_name="mappings")
    intervention_template = models.ForeignKey(
        "interventions.InterventionTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="result_mappings",
    )
    needs_attention = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Mapping {self.scoring_rule}"
