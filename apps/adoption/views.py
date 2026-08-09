"""Public challenge page, family portal, implantation and formations."""
from __future__ import annotations

from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.accounts.models import Role
from apps.accounts.selectors import students_for_user, user_can_access_student
from apps.adoption.models import FormationProgram
from apps.adoption.services import adoption_snapshot, ensure_formation_catalog
from apps.analytics.models import StudentSkillStatus
from apps.core.permissions import FamilyRequiredMixin, ManagementRequiredMixin, NetworkRequiredMixin, user_role_code
from apps.evidences.models import Evidence
from apps.interventions.models import StudentIntervention
from apps.students.models import Student


class PublicHomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            code = user_role_code(request.user)
            if code == Role.Code.FAMILIA:
                return redirect("family:home")
            if code in (Role.Code.PROFESSOR, Role.Code.AEE):
                return redirect("teacher:home")
            if code in (Role.Code.SECRETARIA, Role.Code.TECNICO, Role.Code.SUPERADMIN):
                return redirect("secretaria:dashboard")
            if code:
                return redirect("management:dashboard")
        return render(request, "public/home.html")


class FamilyHomeView(FamilyRequiredMixin, View):
    def get(self, request):
        students = list(students_for_user(request.user).select_related())
        cards = [_family_card(student) for student in students]
        return render(
            request,
            "family/home.html",
            {
                "cards": cards,
                "greeting": request.user.profile.greeting_name if request.user.profile else request.user.first_name,
            },
        )


class FamilyChildView(FamilyRequiredMixin, View):
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk, is_active=True)
        if not user_can_access_student(request.user, student):
            return redirect("family:home")
        card = _family_card(student)
        evidences = Evidence.objects.filter(student=student, is_active=True, visible_to_family=True).select_related("skill")[:12]
        home_tips = _home_tips(card["statuses"])
        return render(
            request,
            "family/child.html",
            {"student": student, "card": card, "evidences": evidences, "home_tips": home_tips},
        )


class ImplantationView(NetworkRequiredMixin, View):
    def get(self, request):
        snapshot = adoption_snapshot()
        return render(request, "admin_panel/implantation.html", {"snapshot": snapshot})


class FormationListView(ManagementRequiredMixin, View):
    def get(self, request):
        ensure_formation_catalog()
        programs = FormationProgram.objects.filter(is_active=True)
        audience = request.GET.get("publico") or ""
        if audience:
            programs = programs.filter(audience=audience)
        return render(
            request,
            "admin_panel/formations.html",
            {
                "programs": programs,
                "audiences": FormationProgram.Audience.choices,
                "audience": audience,
            },
        )


class UsageMonitoringView(NetworkRequiredMixin, View):
    def get(self, request):
        return render(request, "admin_panel/usage.html", {"snapshot": adoption_snapshot()})


def _family_card(student: Student) -> dict:
    enrollment = student.current_enrollment()
    statuses = list(StudentSkillStatus.objects.filter(student=student).select_related("skill", "skill__dimension"))
    attention = [s for s in statuses if s.needs_attention]
    developing = [s for s in statuses if not s.needs_attention]
    if attention:
        headline = "A professora está acompanhando de perto algumas habilidades, com atividades lúdicas."
        tone = "attention"
    elif developing:
        headline = "O desenvolvimento segue em acompanhamento regular na escola."
        tone = "ok"
    else:
        headline = "A sondagem ainda está em andamento. Em breve a professora compartilhará novidades."
        tone = "pending"
    interventions = StudentIntervention.objects.filter(student=student, is_active=True).select_related("skill")[:4]
    return {
        "student": student,
        "enrollment": enrollment,
        "classroom": enrollment.classroom if enrollment else None,
        "headline": headline,
        "tone": tone,
        "statuses": statuses,
        "attention": attention,
        "interventions": interventions,
    }


def _home_tips(statuses) -> list[str]:
    tips = []
    codes = {getattr(s.skill, "bncc_code", "") or s.skill.code for s in statuses if s.skill_id}
    if any("LP07" in c or "rima" in c.lower() for c in codes):
        tips.append("Cantem juntos parlendas e cantigas. Pergunte: “o que rima com gato?”")
    if any("LP06" in c or "segmen" in c.lower() for c in codes):
        tips.append("Batam palmas nas sílabas do nome da criança e de palavras do dia a dia (casa, sol, janela).")
    if any("LP19" in c or "oral" in c.lower() for c in codes):
        tips.append("Peça para recontar uma história ouvida, com apoio de figuras ou do próprio brinquedo.")
    if any("LP03" in c or "compreens" in c.lower() for c in codes):
        tips.append("Depois de ouvir um conto curto, pergunte: quem? onde? o que aconteceu?")
    if not tips:
        tips = [
            "Leiam ou ouçam juntos uma história curta, todos os dias.",
            "Brinquem com rimas, nomes e listas do cotidiano (feira, brinquedos, família).",
            "Valorizem o que a criança já sabe — sem pressa e sem comparação.",
        ]
    tips.append("Se tiverem dúvida, conversem com a professora. Este espaço não substitui o diálogo na escola.")
    return tips[:5]
