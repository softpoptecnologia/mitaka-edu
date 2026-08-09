"""Adoption / usage monitoring and formation catalog."""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role
from apps.adoption.models import FormationProgram
from apps.assessments.models import AssessmentSession
from apps.core.models import AuditLog
from apps.evidences.models import Evidence
from apps.interventions.models import StudentIntervention
from apps.planning.models import PedagogicalPlan
from apps.schools.models import Classroom
from apps.students.models import FamilyLink

User = get_user_model()


FORMATION_SPECS = [
    {
        "title": "Sondagens lúdicas no Infantil e no 1º ano",
        "audience": FormationProgram.Audience.PROFESSOR,
        "objective": "Aplicar instrumentos digitais de forma lúdica, adequada à faixa etária e respeitosa ao desenvolvimento infantil.",
        "duration_hours": 8,
        "modality": FormationProgram.Modality.HIBRIDO,
        "agenda": "Ciclo diagnosticar → planejar → praticar\nUso do tablet/PWA sem degradê e sem arrastar\nRecursos de acesso (áudio, imagem, legendas)\nO que não fazer: rótulo clínico ou ranking de crianças",
        "order": 10,
    },
    {
        "title": "Planejamento a partir da matriz PE / BNCC",
        "audience": FormationProgram.Audience.PROFESSOR,
        "objective": "Planejar a semana com base nos objetivos da rede e nas necessidades identificadas na turma.",
        "duration_hours": 6,
        "modality": FormationProgram.Modality.PRESENCIAL,
        "agenda": "Ler o painel da turma\nEscolher habilidades em atenção\nMontar atividades lúdicas e evidências\nReduzir retrabalho: o sistema sugere, a professora decide",
        "order": 20,
    },
    {
        "title": "Acompanhamento pedagógico na escola",
        "audience": FormationProgram.Audience.COORDENACAO,
        "objective": "Usar relatórios e intervenções para formar professores e acompanhar turmas, sem burocracia extra.",
        "duration_hours": 6,
        "modality": FormationProgram.Modality.PRESENCIAL,
        "agenda": "Painel da escola e necessidades pedagógicas\nTemplates de intervenção\nHT e formação em serviço\nConversar com famílias sem rótulos",
        "order": 30,
    },
    {
        "title": "Gestão escolar com evidências",
        "audience": FormationProgram.Audience.GESTAO,
        "objective": "Acompanhar cobertura de sondagem, pendências e uso da plataforma na escola.",
        "duration_hours": 4,
        "modality": FormationProgram.Modality.HIBRIDO,
        "agenda": "Indicadores da escola (não ranqueamento punitivo)\nImportação de matrículas\nRotina de suporte interno\nPrivacidade e LGPD na ponta",
        "order": 40,
    },
    {
        "title": "Painéis da rede e decisões da Secretaria",
        "audience": FormationProgram.Audience.TECNICO,
        "objective": "Ler indicadores por estudante, turma, escola e rede para orientar formação e acompanhamento.",
        "duration_hours": 8,
        "modality": FormationProgram.Modality.PRESENCIAL,
        "agenda": "Recortes municipais\nComparar escolas com cuidado ético\nFormação continuada a partir dos dados\nMonitorar implantação e uso",
        "order": 50,
    },
    {
        "title": "Família na rede: acompanhar sem comparar",
        "audience": FormationProgram.Audience.FAMILIA,
        "objective": "Mostrar o portal da família e práticas simples em casa alinhadas à escola.",
        "duration_hours": 2,
        "modality": FormationProgram.Modality.EAD,
        "agenda": "O que a família vê (e o que não vê)\nJogos de parlenda e palmas em casa\nQuando procurar a professora\nNão é diagnóstico clínico",
        "order": 60,
    },
]


def ensure_formation_catalog() -> list[FormationProgram]:
    programs = []
    for spec in FORMATION_SPECS:
        program, _ = FormationProgram.objects.update_or_create(
            title=spec["title"],
            defaults={**spec, "is_active": True},
        )
        programs.append(program)
    return programs


def adoption_snapshot() -> dict:
    now = timezone.now()
    since = now - timedelta(days=30)
    teachers = User.objects.filter(is_active=True, userprofile__role__code=Role.Code.PROFESSOR)
    teacher_count = teachers.count()
    active_logins = (
        AuditLog.objects.filter(action=AuditLog.Action.LOGIN, created_at__gte=since, actor_id__in=teachers.values("id"))
        .values("actor_id")
        .distinct()
        .count()
    )
    classrooms = Classroom.objects.filter(is_active=True, school_year__is_active=True)
    classroom_count = classrooms.count()
    classrooms_with_session = (
        AssessmentSession.objects.filter(
            status=AssessmentSession.Status.COMPLETED,
            is_active=True,
            enrollment__classroom__in=classrooms,
        )
        .values("enrollment__classroom_id")
        .distinct()
        .count()
    )
    evidences = Evidence.objects.filter(is_active=True).count()
    shared = Evidence.objects.filter(is_active=True, visible_to_family=True).count()
    plans = PedagogicalPlan.objects.filter(is_active=True).count()
    interventions = StudentIntervention.objects.filter(is_active=True).count()
    families = FamilyLink.objects.filter(is_active=True).values("user_id").distinct().count()
    sessions = AssessmentSession.objects.filter(is_active=True, status=AssessmentSession.Status.COMPLETED).count()

    def pct(part, total):
        if not total:
            return 0
        return round(100 * part / total)

    return {
        "teacher_count": teacher_count,
        "teachers_active_30d": active_logins,
        "teachers_active_pct": pct(active_logins, teacher_count),
        "classroom_count": classroom_count,
        "classrooms_with_session": classrooms_with_session,
        "classroom_coverage_pct": pct(classrooms_with_session, classroom_count),
        "completed_sessions": sessions,
        "evidences": evidences,
        "evidences_shared_family": shared,
        "plans": plans,
        "interventions": interventions,
        "family_links": families,
        "formation_count": FormationProgram.objects.filter(is_active=True).count(),
    }
