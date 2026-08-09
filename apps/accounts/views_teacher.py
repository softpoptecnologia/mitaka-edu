"""Teacher portal views."""
from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.accounts.selectors import (
    classrooms_for_user,
    user_can_access_classroom,
    user_can_access_student,
)
from apps.accessibility.models import AccessibilityFeature, StudentSupportPlan
from apps.accessibility.permissions import (
    active_resource_labels_for_teacher,
    can_change_accessibility_profile,
    can_manage_support_plan,
    can_view_accessibility_profile,
)
from apps.accessibility.services.catalog import ensure_default_features
from apps.accessibility.services.profile import set_student_features
from apps.analytics.models import StudentSkillStatus
from apps.assessments.models import AssessmentInstrument, AssessmentSession
from apps.core.permissions import TeacherRequiredMixin
from apps.curriculum.models import Skill
from apps.evidences.forms import EvidenceForm
from apps.evidences.models import Evidence
from apps.interventions.forms import StudentInterventionForm
from apps.interventions.models import ClassroomIntervention, InterventionStatus, InterventionTemplate, StudentIntervention
from apps.interventions.services.grouping import suggest_groups
from apps.interventions.services.labels import day_greeting, first_name
from apps.interventions.services.snapshot import load_classroom_snapshot, load_snapshots_for_user
from apps.interventions.services.student_synthesis import build_student_synthesis
from apps.interventions.services.teacher_actions import build_teacher_action_queue
from apps.planning.models import PedagogicalPlan, PlanActivity
from apps.schools.models import Classroom
from apps.students.models import Enrollment, Student


class TeacherHomeView(TeacherRequiredMixin, View):
    def get(self, request):
        queue = build_teacher_action_queue(request.user)
        snapshots = queue.snapshots or load_snapshots_for_user(request.user)
        primary = snapshots[0] if snapshots else None
        profile = request.user.profile
        full_greeting = profile.greeting_name if profile else request.user.first_name or request.user.username
        classroom_cards = []
        for snapshot in snapshots:
            summary = snapshot.summary_counts()
            classroom_cards.append({"classroom": snapshot.classroom, **summary})
        return render(
            request,
            "teacher/home.html",
            {
                "greeting_name": first_name(full_greeting),
                "day_greeting": day_greeting(),
                "primary_classroom": primary.classroom if primary else None,
                "primary_summary": primary.summary_counts() if primary else None,
                "actions": queue.actions,
                "action_count": queue.count,
                "classroom_cards": classroom_cards,
                "empty": not queue.actions,
            },
        )


class TeacherClassroomListView(TeacherRequiredMixin, View):
    def get(self, request):
        classrooms = classrooms_for_user(request.user).filter(school_year__is_active=True)
        return render(request, "teacher/classroom_list.html", {"classrooms": classrooms})


class TeacherClassroomDetailView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            messages.error(request, "Você não tem acesso a esta turma.")
            return redirect("teacher:home")
        snapshot = load_classroom_snapshot(classroom)
        status_filter = request.GET.get("filtro", "todos")
        q = (request.GET.get("q") or "").strip()
        apoio = request.GET.get("apoio") == "1"
        rows = []
        summary = snapshot.summary_counts()
        for record in snapshot.records:
            student = record.student
            if record.needs_attention:
                badge, label = "attention", "Maior mediação"
            elif record.has_completed_session:
                badge, label = "ok", "Acompanhando bem"
            else:
                badge, label = "pending", "Aguarda observação"
            if status_filter == "pendentes" and badge != "pending":
                continue
            if status_filter == "acompanhamento" and badge != "ok":
                continue
            if status_filter == "atencao" and badge != "attention":
                continue
            if apoio and not record.feature_codes:
                continue
            if q and q.lower() not in student.full_name.lower() and q.lower() not in (student.external_code or "").lower():
                continue
            rows.append(
                {
                    "enrollment": record.enrollment,
                    "student": student,
                    "badge": badge,
                    "label": label,
                    "has_a11y": bool(record.feature_codes),
                    "resources": record.feature_names,
                }
            )
        needs = [
            g
            for g in suggest_groups(snapshot, include_consolidation=False)
            if g.kind != "consolidation"
        ]
        return render(
            request,
            "teacher/classroom_detail.html",
            {
                "classroom": classroom,
                "rows": rows,
                "filter": status_filter,
                "q": q,
                "apoio": apoio,
                "summary": summary,
                "total": summary["total"],
                "needs": needs,
            },
        )


class StudentProfileView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            messages.error(request, "Você não tem acesso a este estudante.")
            return redirect("teacher:home")
        enrollment = student.current_enrollment()
        synthesis = None
        if enrollment and user_can_access_classroom(request.user, enrollment.classroom):
            snapshot = load_classroom_snapshot(enrollment.classroom)
            synthesis = build_student_synthesis(snapshot, student.pk)
        tab = request.GET.get("tab", "geral")
        q_status = request.GET.get("status", "")
        q_skill = request.GET.get("habilidade", "")
        q_modo = request.GET.get("modo", "")
        instruments = AssessmentInstrument.objects.filter(is_active=True, is_published=True).select_related("skill")
        sessions = AssessmentSession.objects.filter(enrollment__student=student).select_related(
            "instrument", "instrument__skill"
        ).order_by("-started_at")
        if q_status:
            sessions = sessions.filter(status=q_status)
        if q_modo == "adapted":
            sessions = sessions.exclude(active_features=[])
        if q_skill:
            sessions = sessions.filter(instrument__skill_id=q_skill)
        evidences = Evidence.objects.filter(student=student, is_active=True).select_related(
            "skill", "recorded_by"
        ).order_by("-recorded_at")
        if q_skill:
            evidences = evidences.filter(skill_id=q_skill)
        interventions = StudentIntervention.objects.filter(student=student, is_active=True).select_related(
            "skill", "responsible"
        ).order_by("-starts_on", "-created_at")
        if q_status and tab == "intervencoes":
            interventions = interventions.filter(status=q_status)
        if q_skill:
            interventions = interventions.filter(skill_id=q_skill)
        statuses = StudentSkillStatus.objects.filter(student=student).select_related("skill", "last_session")
        trajectory = student.enrollments.filter(is_active=True).select_related(
            "classroom", "school_year", "classroom__school"
        ).order_by("school_year__year", "enrolled_at")
        resource_labels = (
            active_resource_labels_for_teacher(student)
            if can_view_accessibility_profile(request.user, student)
            else []
        )
        support_plans = StudentSupportPlan.objects.filter(student=student, is_active=True).prefetch_related(
            "strategies", "strategies__accessibility_feature"
        ).order_by("-start_date", "-created_at")
        if tab == "apoio":
            ensure_default_features()
        all_features = AccessibilityFeature.objects.filter(is_active=True).select_related("category")
        profile = getattr(student, "accessibility_profile", None)
        active_codes = profile.active_feature_codes() if profile else []
        return render(
            request,
            "teacher/student_profile.html",
            {
                "student": student,
                "enrollment": enrollment,
                "synthesis": synthesis,
                "tab": tab,
                "instruments": instruments,
                "sessions": sessions,
                "evidences": evidences,
                "interventions": interventions,
                "statuses": statuses,
                "trajectory": trajectory,
                "attention_skills": statuses.filter(needs_attention=True),
                "resource_labels": resource_labels,
                "support_plans": support_plans,
                "can_edit_accessibility": can_change_accessibility_profile(request.user, student),
                "can_manage_support_plan": can_manage_support_plan(request.user, student),
                "intervention_statuses": InterventionStatus.choices,
                "all_features": all_features,
                "active_feature_codes": active_codes,
                "q_status": q_status,
                "q_skill": q_skill,
                "q_modo": q_modo,
                "skills": Skill.objects.filter(
                    id__in=list(statuses.values_list("skill_id", flat=True))
                    + list(instruments.values_list("skill_id", flat=True))
                ).distinct().order_by("name"),
                "chart_labels": [s.skill.name for s in statuses],
                "chart_scores": [
                    round(100 * (s.raw_score or 0) / s.max_score, 1) if s.max_score else 0 for s in statuses
                ],
            },
        )


class SessionResultView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        session = get_object_or_404(AssessmentSession, pk=pk)
        if not user_can_access_student(request.user, session.enrollment.student):
            messages.error(request, "Acesso negado.")
            return redirect("teacher:home")
        results = session.skill_results.select_related("skill", "recommended_template")
        responses = session.responses.select_related("item", "variant_used").order_by("item__order")
        return render(
            request,
            "teacher/session_result.html",
            {
                "session": session,
                "results": results,
                "student": session.enrollment.student,
                "responses": responses,
            },
        )


class UpdateAccessibilityProfileView(TeacherRequiredMixin, View):
    """AEE / coordination may update functional accessibility resources."""

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not can_change_accessibility_profile(request.user, student):
            messages.error(request, "Você não tem permissão para alterar o perfil de acessibilidade.")
            return redirect("teacher:student", pk=student.pk)
        codes = request.POST.getlist("features")
        notes = request.POST.get("notes", "")
        set_student_features(student=student, feature_codes=codes, actor=request.user, notes=notes)
        messages.success(request, "Recursos de acessibilidade atualizados.")
        return redirect("teacher:student", pk=student.pk)


class EvidenceCreateView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            return redirect("teacher:home")
        form = EvidenceForm(student=student)
        return render(request, "teacher/evidence_form.html", {"form": form, "student": student})

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            return redirect("teacher:home")
        form = EvidenceForm(request.POST, request.FILES, student=student)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.student = student
            evidence.enrollment = student.current_enrollment()
            evidence.recorded_by = request.user
            uploaded = evidence.file
            if uploaded:
                name = uploaded.name.lower()
                if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    evidence.file_type = Evidence.FileType.PHOTO
                elif name.endswith((".mp3", ".wav", ".ogg", ".webm")):
                    evidence.file_type = Evidence.FileType.AUDIO
                elif name.endswith((".mp4", ".webm")):
                    evidence.file_type = Evidence.FileType.VIDEO
            elif evidence.description:
                evidence.file_type = Evidence.FileType.TEXT
            evidence.save()
            messages.success(request, "Evidência registrada.")
            return redirect("teacher:student", pk=student.pk)
        return render(request, "teacher/evidence_form.html", {"form": form, "student": student})


class InterventionCreateView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            return redirect("teacher:home")
        template_id = request.GET.get("template")
        initial = {}
        if template_id:
            template = get_object_or_404(InterventionTemplate, pk=template_id)
            initial = {
                "skill": template.skill_id,
                "objective": template.objective,
                "activities": template.suggested_activities,
            }
        form = StudentInterventionForm(initial=initial, student=student)
        return render(
            request,
            "teacher/intervention_form.html",
            {"form": form, "student": student, "template_id": template_id},
        )

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            return redirect("teacher:home")
        form = StudentInterventionForm(request.POST, student=student)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.student = student
            obj.enrollment = student.current_enrollment()
            obj.responsible = request.user
            template_id = request.POST.get("template_id")
            if template_id:
                obj.template_id = template_id
            if not obj.starts_on:
                obj.starts_on = timezone.localdate()
            obj.save()
            messages.success(request, "Intervenção adicionada.")
            return redirect("teacher:student", pk=student.pk)
        return render(request, "teacher/intervention_form.html", {"form": form, "student": student})


class AcceptInterventionTemplateView(TeacherRequiredMixin, View):
    def post(self, request, pk, template_id):
        student = get_object_or_404(Student, pk=pk)
        if not user_can_access_student(request.user, student):
            return redirect("teacher:home")
        template = get_object_or_404(InterventionTemplate, pk=template_id)
        enrollment = student.current_enrollment()
        StudentIntervention.objects.create(
            enrollment=enrollment,
            student=student,
            skill=template.skill,
            template=template,
            responsible=request.user,
            objective=template.objective,
            activities=template.suggested_activities,
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=template.suggested_duration_days),
        )
        messages.success(request, "Intervenção sugerida adicionada.")
        return redirect("teacher:student", pk=student.pk)


class ClassroomPlanningView(TeacherRequiredMixin, View):
    def get(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            return redirect("teacher:home")
        insights = []
        enrollments = classroom.enrollments.filter(is_active=True)
        total = enrollments.count() or 1
        for skill in Skill.objects.filter(dimension__matrix_version__is_published=True).distinct():
            needy = StudentSkillStatus.objects.filter(
                enrollment__classroom=classroom,
                skill=skill,
                needs_attention=True,
            ).count()
            if needy:
                insights.append(
                    {
                        "skill": skill,
                        "needy": needy,
                        "total": enrollments.count(),
                        "pct": round(100 * needy / total),
                        "template": InterventionTemplate.objects.filter(skill=skill, is_active=True).first(),
                    }
                )
        insights.sort(key=lambda x: x["needy"], reverse=True)
        plans = classroom.plans.filter(is_active=True)
        return render(
            request,
            "teacher/planning.html",
            {"classroom": classroom, "insights": insights, "plans": plans},
        )

    def post(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        if not user_can_access_classroom(request.user, classroom):
            return redirect("teacher:home")
        skill_id = request.POST.get("skill_id")
        template_id = request.POST.get("template_id")
        skill = get_object_or_404(Skill, pk=skill_id)
        template = InterventionTemplate.objects.filter(pk=template_id).first() if template_id else None
        intervention = ClassroomIntervention.objects.create(
            classroom=classroom,
            skill=skill,
            template=template,
            responsible=request.user,
            objective=template.objective if template else f"Fortalecer {skill.name}",
            activities=template.suggested_activities if template else "",
            starts_on=timezone.localdate(),
        )
        plan = PedagogicalPlan.objects.create(
            classroom=classroom,
            title=f"Plano — {skill.name}",
            skill=skill,
            created_by=request.user,
            classroom_intervention=intervention,
        )
        if template:
            for i, line in enumerate(template.activities_list()):
                PlanActivity.objects.create(plan=plan, title=line, order=i)
        messages.success(request, "Intervenção de turma e planejamento criados.")
        return redirect("teacher:planning", pk=classroom.pk)
