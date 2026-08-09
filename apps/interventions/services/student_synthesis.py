"""Short pedagogical synthesis for the student profile."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.interventions.models import FollowupResult
from apps.interventions.services.labels import skill_label
from apps.interventions.services.reassessment import suggestions_for_snapshot


FOLLOWUP_LABELS = {
    FollowupResult.PROGRESSED: "Apresentou avanço",
    FollowupResult.NEEDS_MORE_SUPPORT: "Ainda precisa de apoio",
    FollowupResult.NOT_OBSERVED: "Não foi possível observar",
}


@dataclass
class StudentSynthesis:
    main_need: str | None = None
    main_skill_id: int | None = None
    last_intervention_title: str | None = None
    last_followup_label: str | None = None
    next_action: str | None = None
    next_action_url: str | None = None
    next_action_kind: str = ""

    def to_dict(self) -> dict:
        return {
            "main_need": self.main_need,
            "main_skill_id": self.main_skill_id,
            "last_intervention_title": self.last_intervention_title,
            "last_followup_label": self.last_followup_label,
            "next_action": self.next_action,
            "next_action_url": self.next_action_url,
            "next_action_kind": self.next_action_kind,
        }


def build_student_synthesis(snapshot, student_id: int) -> StudentSynthesis:
    record = snapshot.records_by_student_id.get(student_id)
    if record is None:
        return StudentSynthesis()
    attention = [s for s in record.statuses if s.needs_attention]
    attention.sort(key=lambda s: (0 if s.status_code == "needs_support" else 1, s.skill.name))
    main_status = attention[0] if attention else None
    last_iv = record.interventions[0] if record.interventions else None
    synthesis = StudentSynthesis(
        main_need=skill_label(main_status.skill) if main_status else None,
        main_skill_id=main_status.skill_id if main_status else None,
        last_intervention_title=(
            last_iv.template.title if last_iv and last_iv.template_id else (last_iv.objective[:80] if last_iv else None)
        ),
        last_followup_label=FOLLOWUP_LABELS.get(last_iv.followup_result) if last_iv else None,
    )
    reassess = next((item for item in suggestions_for_snapshot(snapshot) if item.student_id == student_id), None)
    if reassess:
        synthesis.next_action = f"Nova observação de {reassess.skill_name}"
        synthesis.next_action_kind = "reassessment"
        if reassess.instrument_id:
            synthesis.next_action_url = reverse("assessment:preview", args=[reassess.enrollment_id, reassess.instrument_id])
        else:
            synthesis.next_action_url = reverse("teacher:student", args=[student_id]) + "?tab=avaliacoes"
        return synthesis
    open_iv = next((iv for iv in record.interventions if not iv.has_followup and iv.status in {"planned", "in_progress"}), None)
    if open_iv:
        synthesis.next_action = "Registrar acompanhamento da atividade"
        synthesis.next_action_kind = "followup"
        if open_iv.classroom_intervention_id:
            synthesis.next_action_url = reverse("teacher:quick_followup", args=[open_iv.classroom_intervention_id])
        else:
            synthesis.next_action_url = reverse("teacher:quick_followup_student", args=[open_iv.pk])
        return synthesis
    if main_status:
        synthesis.next_action = f"Trabalhar {skill_label(main_status.skill)}"
        synthesis.next_action_kind = "intervention"
        synthesis.next_action_url = reverse("teacher:suggested_group", args=[snapshot.classroom.pk, main_status.skill_id])
        return synthesis
    if not record.has_completed_session:
        synthesis.next_action = "Iniciar observação"
        synthesis.next_action_kind = "assessment"
        synthesis.next_action_url = reverse("teacher:student", args=[student_id]) + "?tab=avaliacoes"
        return synthesis
    synthesis.next_action = "Acompanhar consolidação"
    synthesis.next_action_url = reverse("teacher:classroom", args=[snapshot.classroom.pk])
    return synthesis
