"""Seed demonstrative data for Jucati/PE pitch."""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User, UserProfile
from apps.accessibility.models import (
    StudentAccessibilityProfile,
    StudentSupportPlan,
    StudentSupportStrategy,
)
from apps.accessibility.services.catalog import ensure_default_features
from apps.accessibility.services.profile import set_student_features
from apps.analytics.models import AggregatedIndicator, StudentSkillStatus
from apps.analytics.services.aggregate import rebuild_attention_indicators
from apps.assessments.models import (
    AssessmentInstrument,
    AssessmentItem,
    AssessmentItemVariant,
    AssessmentOption,
    AssessmentResponse,
    AssessmentSession,
    ItemAccessRequirement,
    ScoringRule,
    SkillResultMapping,
)
from apps.assessments.services.scoring import score_session
from apps.curriculum.models import (
    DevelopmentDimension,
    MatrixVersion,
    PedagogicalMatrix,
    Skill,
    SkillProgression,
    StatusLabelConfig,
)
from apps.assessments.services.session import complete_session, save_response, start_session
from apps.evidences.models import Evidence
from apps.interventions.models import (
    ClassroomIntervention,
    FollowupResult,
    InterventionStatus,
    InterventionTemplate,
    StudentIntervention,
)
from apps.planning.models import PedagogicalPlan, PlanActivity
from apps.schools.models import Classroom, Municipality, School, SchoolYear, TeacherClassroom
from apps.adoption.services import ensure_formation_catalog
from apps.students.models import Enrollment, FamilyLink, Student


DEMO_PASSWORD = "demo1234"


class Command(BaseCommand):
    help = "Cria dados demonstrativos para o MVP Mitaka Edu (Jucati/PE)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Criando roles e usuários...")
        roles = self._roles()
        users = self._users(roles)
        self.stdout.write("Criando rede escolar...")
        municipality, schools, year_2025, year_2026, classrooms = self._schools(users)
        self.stdout.write("Criando estudantes e matrículas...")
        students = self._students(classrooms, year_2025, year_2026)
        self.stdout.write("Criando matriz pedagógica...")
        version, skills, instruments = self._curriculum()
        self._retire_legacy_curriculum(version, skills)
        self.stdout.write("Configurando acessibilidade e apoio inclusivo...")
        self._accessibility(users, students, year_2026, instruments)
        self.stdout.write("Criando respostas simuladas...")
        self._sessions(users["professor"], users["professor2"], students, classrooms, instruments, skills)
        self.stdout.write("Vinculando família e formações da rede...")
        self._family_and_adoption(users, students)
        rebuild_attention_indicators(year_2026)
        self.stdout.write(self.style.SUCCESS("seed_demo concluído."))
        self.stdout.write("Usuários demo (senha: demo1234):")
        for key, user in users.items():
            self.stdout.write(f"  - {key}: {user.username}")

    def _roles(self):
        mapping = {}
        for code, name in Role.Code.choices:
            role, _ = Role.objects.update_or_create(code=code, defaults={"name": name})
            mapping[code] = role
        return mapping

    def _users(self, roles):
        def make(username, first, role_code, school=None):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "email": f"{username}@mitaka.local"},
            )
            user.set_password(DEMO_PASSWORD)
            user.first_name = first
            user.is_active = True
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "role": roles[role_code],
                    "display_name": first,
                    "school": school,
                },
            )
            user.refresh_from_db()
            return user

        # schools created later — assign school after
        users = {
            "superadmin": make("admin", "Admin", Role.Code.SUPERADMIN),
            "secretaria": make("secretaria", "Carla Secretaria", Role.Code.SECRETARIA),
            "tecnico": make("tecnico", "Paulo Técnico", Role.Code.TECNICO),
            "gestor": make("gestor", "Helena Gestora", Role.Code.GESTOR),
            "coordenador": make("coordenador", "Rita Coordenadora", Role.Code.COORDENADOR),
            "aee": make("aee", "Marina AEE", Role.Code.AEE),
            "professor": make("professora", "Ana Professora", Role.Code.PROFESSOR),
            "professor2": make("professor2", "Bruno Professor", Role.Code.PROFESSOR),
            "familia": make("familia", "Lúcia Responsável", Role.Code.FAMILIA),
        }
        users["superadmin"].is_staff = True
        users["superadmin"].is_superuser = True
        users["superadmin"].save()
        return users

    def _schools(self, users):
        municipality, _ = Municipality.objects.get_or_create(
            slug="jucati",
            defaults={"name": "Jucati", "state": "PE"},
        )
        year_2025, _ = SchoolYear.objects.get_or_create(year=2025, defaults={"label": "2025", "is_active": False})
        year_2026, _ = SchoolYear.objects.update_or_create(
            year=2026, defaults={"label": "2026", "is_active": True, "starts_on": date(2026, 2, 1)}
        )
        schools_data = [
            ("Creche Municipal Maria Inez de Melo", "ESC001", "Educação Infantil"),
            ("Creche Municipal Noêmia Eloy de Melo (Tia Noêmia)", "ESC002", "Educação Infantil"),
            ("Escola Albino Moreira", "ESC003", "Ensino Fundamental · Centro"),
            ("Escola Municipal Vereador Eliel Peixoto de Melo", "ESC004", "Vila Neves / Zona Rural"),
            ("Escola Municipal Ananias Crisóstomo", "ESC005", ""),
            ("Escola Municipal Deputado Airon Rios", "ESC006", ""),
            ("Escola Antonio Alves de Pontes", "ESC007", ""),
            ("Escola José Ferreira da Silva", "ESC008", ""),
            ("EREM Henrique Justino de Melo", "ESC009", "Ensino Médio · rede estadual"),
        ]
        schools = []
        for name, code, address in schools_data:
            school, _ = School.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "municipality": municipality,
                    "address": address,
                    "is_active": True,
                },
            )
            schools.append(school)

        UserProfile.objects.filter(user=users["gestor"]).update(school=schools[0])
        UserProfile.objects.filter(user=users["coordenador"]).update(school=schools[0])
        UserProfile.objects.filter(user=users["aee"]).update(school=schools[0])
        UserProfile.objects.filter(user=users["professor"]).update(school=schools[0])
        UserProfile.objects.filter(user=users["professor2"]).update(school=schools[1])

        # Rede fictícia anterior: 1º Ano em ESC002 e Inf IV/V em ESC003.
        for from_code, year, name, target in [
            ("ESC002", year_2026, "1º Ano A", schools[2]),
            ("ESC003", year_2026, "Infantil IV A", schools[3]),
            ("ESC003", year_2026, "Infantil V A", schools[4]),
        ]:
            source = (
                Classroom.objects.filter(school__code=from_code, school_year=year, name=name)
                .exclude(school=target)
                .first()
            )
            if not source:
                continue
            dest_exists = Classroom.objects.filter(school=target, school_year=year, name=name).exists()
            if dest_exists:
                source.is_active = False
                source.save(update_fields=["is_active", "updated_at"])
            else:
                source.school = target
                source.is_active = True
                source.save(update_fields=["school", "is_active", "updated_at"])

        classrooms = []
        specs = [
            (schools[0], year_2026, "Infantil V A", "Infantil V"),  # Maria Inez
            (schools[0], year_2026, "Infantil V B", "Infantil V"),
            (schools[1], year_2026, "Infantil V A", "Infantil V"),  # Tia Noêmia
            (schools[2], year_2026, "1º Ano A", "1º Ano"),  # Albino Moreira (Centro)
            (schools[3], year_2026, "Infantil IV A", "Infantil IV"),  # Eliel Peixoto (rural)
            (schools[4], year_2026, "Infantil V A", "Infantil V"),  # Ananias Crisóstomo
            (schools[0], year_2025, "Infantil IV A", "Infantil IV"),
        ]
        for school, year, name, grade in specs:
            room, _ = Classroom.objects.update_or_create(
                school=school,
                school_year=year,
                name=name,
                defaults={"grade_label": grade, "is_active": True},
            )
            classrooms.append(room)

        intended_ids = {c.pk for c in classrooms}
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor"], classroom=classrooms[0], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor"], classroom=classrooms[1], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor"], classroom=classrooms[4], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor"], classroom=classrooms[5], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor2"], classroom=classrooms[2], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.update_or_create(
            teacher=users["professor2"], classroom=classrooms[3], defaults={"is_primary": True}
        )
        TeacherClassroom.objects.filter(
            teacher__in=[users["professor"], users["professor2"]],
        ).exclude(classroom_id__in=intended_ids).delete()
        return municipality, schools, year_2025, year_2026, classrooms

    def _students(self, classrooms, year_2025, year_2026):
        names = [
            "Luna Ferreira", "Theo Martins", "Alice Rocha", "Benício Souza", "Helena Dias",
            "Gael Oliveira", "Laura Mendes", "Noah Barbosa", "Valentina Costa", "Arthur Lima",
            "Manuela Alves", "Davi Cardoso", "Isis Ribeiro", "Samuel Pinto", "Cecília Nunes",
            "Bernardo Teixeira", "Liz Carvalho", "Heitor Ramos", "Aurora Freitas", "Miguel Correia",
            "Maya Duarte", "Benjamin Lopes", "Eloá Moreira", "Joaquim Azevedo", "Lizandra Pires",
            "Ravi Monteiro", "Olívia Castro", "Caleb Moura", "Ísis Fernandes", "Enzo Batista",
        ]
        students = []
        targets = classrooms[:6]
        va_indexes = {0, 1, 6, 7, 8, 9, 10, 15, 20}  # Infantil V A — jornada da professora
        remaining_rooms = classrooms[1:6]
        remaining_i = 0
        for i, name in enumerate(names):
            code = f"JUC{2026}{i+1:03d}"
            student, _ = Student.objects.update_or_create(
                external_code=code,
                defaults={
                    "full_name": name,
                    "birth_date": date(2020, 1, 1) + timedelta(days=i * 40),
                    "is_active": True,
                },
            )
            if i in va_indexes:
                room = classrooms[0]
            else:
                room = remaining_rooms[remaining_i % len(remaining_rooms)]
                remaining_i += 1
            Enrollment.objects.update_or_create(
                student=student,
                school_year=year_2026,
                defaults={"classroom": room, "status": Enrollment.Status.ACTIVE, "is_active": True},
            )
            students.append(student)

        # Longitudinal history for first student
        luna = students[0]
        Enrollment.objects.update_or_create(
            student=luna,
            school_year=year_2025,
            defaults={
                "classroom": classrooms[6],
                "status": Enrollment.Status.COMPLETED,
                "is_active": True,
            },
        )
        return students

    def _curriculum(self):
        matrix, _ = PedagogicalMatrix.objects.update_or_create(
            name="Matriz Alfabetizar Letrando — PE",
            defaults={
                "description": (
                    "Matriz demonstrativa alinhada ao Currículo de Pernambuco e à BNCC "
                    "(Língua Portuguesa — Anos Iniciais), na perspectiva de alfabetizar letrando. "
                    "Não constitui instrumento clínico nem diagnóstico médico."
                ),
                "is_active": True,
            },
        )
        # Keep legacy name matrix if it exists for continuity of demos
        PedagogicalMatrix.objects.filter(name="Matriz Precursoras Leitura e Escrita").update(is_active=False)

        version, _ = MatrixVersion.objects.update_or_create(
            matrix=matrix,
            version_label="2026-v1-PE",
            defaults={
                "is_published": True,
                "published_at": timezone.now(),
                "framework_reference": "Currículo de Pernambuco / BNCC — Língua Portuguesa (Anos Iniciais)",
                "notes": (
                    "Versão demonstrativa para acompanhamento pedagógico na transição "
                    "Educação Infantil → Anos Iniciais. Ênfase nos 1º e 2º anos (alfabetização "
                    "associada ao letramento), com práticas lúdicas e gêneros do cotidiano "
                    "(parlendas, cantigas, listas), conforme Currículo PE."
                ),
            },
        )
        # Unpublish older demo version if present
        MatrixVersion.objects.filter(version_label="2026-v1").exclude(pk=version.pk).update(is_published=False)

        labels = [
            ("not_observed", "Não observado", 0, "○"),
            ("needs_support", "Necessita maior mediação", 1, "⚠"),
            ("developing_with_support", "Desenvolvendo com apoio", 2, "…"),
            ("developing", "Em desenvolvimento", 3, "↗"),
            ("demonstrated", "Habilidade demonstrada", 4, "✓"),
        ]
        for i, (code, label, sev, icon) in enumerate(labels):
            StatusLabelConfig.objects.update_or_create(
                matrix_version=version,
                code=code,
                defaults={"label": label, "severity": sev, "icon": icon, "order": i},
            )

        # Dimensões alinhadas às práticas de linguagem / objetos do Currículo PE
        skill_specs = [
            {
                "dim_code": "oralidade",
                "dim_name": "Oralidade",
                "practice_axis": "Oralidade",
                "skill_code": "EF15LP19PE",
                "bncc_code": "EF15LP19PE",
                "name": "Recontar oralmente textos literários",
                "knowledge_object": "Contagem de histórias / tradição oral",
                "description": "Recontar oralmente, com e sem apoio de imagem, textos literários (contos, cordéis, cantigas, parlendas).",
                "curriculum_notes": "Currículo PE — campo artístico-literário. Valoriza a mediação e o repertório regional.",
                "activities": (
                    "Roda de contação com imagens\n"
                    "Reconto de parlendas e cantigas locais\n"
                    "Escuta e reconto em pequenos grupos"
                ),
            },
            {
                "dim_code": "compreensao_oral",
                "dim_name": "Leitura/escuta compartilhada",
                "practice_axis": "Leitura/escuta (compartilhada e autônoma)",
                "skill_code": "EF15LP03PE",
                "bncc_code": "EF15LP03PE",
                "name": "Localizar informações explícitas em textos ouvidos/lidos",
                "knowledge_object": "Estratégias de leitura/escuta",
                "description": "Localizar informações explícitas em diferentes gêneros lidos, ouvidos e/ou sinalizados.",
                "curriculum_notes": "Currículo PE — leitura/escuta em todos os campos de atuação.",
                "activities": (
                    "Escuta de histórias com perguntas significativas\n"
                    "Identificação de personagens e acontecimentos\n"
                    "Leitura compartilhada de cantigas e poemas"
                ),
            },
            {
                "dim_code": "vocabulario",
                "dim_name": "Vocabulário em uso",
                "practice_axis": "Análise linguística/semiótica",
                "skill_code": "EF01LP15PE",
                "bncc_code": "EF01LP15PE",
                "name": "Agrupar palavras por aproximação de significado",
                "knowledge_object": "Sinonímia e antonímia / semântica",
                "description": "Agrupar palavras por aproximação de significado e separar por oposição, a partir de práticas de leitura.",
                "curriculum_notes": "Currículo PE — trabalho semântico em contextos de leitura, não listas isoladas.",
                "activities": (
                    "Listas de palavras do mesmo campo semântico\n"
                    "Jogos de sinônimos com objetos da sala\n"
                    "Exploração de nomes, frutas e brinquedos preferidos"
                ),
            },
            {
                "dim_code": "consciencia_fonologica",
                "dim_name": "Consciência fonológica",
                "practice_axis": "Análise linguística/semiótica (Alfabetização)",
                "skill_code": "EF01LP09PE",
                "bncc_code": "EF01LP09PE",
                "name": "Comparar sons de sílabas em palavras conhecidas",
                "knowledge_object": "Construção do sistema alfabético",
                "description": (
                    "Comparar palavras, identificando semelhanças e diferenças entre sons de sílabas "
                    "iniciais, mediais e finais, a partir de textos conhecidos."
                ),
                "curriculum_notes": (
                    "Currículo PE define consciência fonológica como capacidade metalinguística de perceber "
                    "frases, palavras, sílabas e fonemas — sempre em contextos de uso da língua, "
                    "não como treino fônico isolado."
                ),
                "activities": (
                    "Análise sonora com nomes da turma\n"
                    "Jogos de sílabas iniciais/finais com parlendas\n"
                    "Comparação de palavras em listas do cotidiano"
                ),
            },
            {
                "dim_code": "rimas",
                "dim_name": "Rimas e jogos sonoros",
                "practice_axis": "Análise linguística / Campo artístico-literário",
                "skill_code": "EF12LP07PE",
                "bncc_code": "EF12LP07PE",
                "name": "Identificar e reproduzir rimas em textos de tradição oral",
                "knowledge_object": "Forma de composição de textos versificados",
                "description": (
                    "Identificar e (re)produzir, em cantigas, quadras, parlendas, trava-línguas e canções, "
                    "rimas, aliterações e outros jogos sonoros."
                ),
                "curriculum_notes": "Currículo PE — gêneros da tradição oral como objeto de análise e prazer estético.",
                "activities": (
                    "Jogo de pares que rimam\n"
                    "Parlendas e cantigas regionais\n"
                    "Identificação de sons finais em versos conhecidos"
                ),
            },
            {
                "dim_code": "segmentacao",
                "dim_name": "Segmentação silábica",
                "practice_axis": "Análise linguística/semiótica (Alfabetização)",
                "skill_code": "EF01LP06PE",
                "bncc_code": "EF01LP06PE",
                "name": "Segmentar oralmente palavras em sílabas",
                "knowledge_object": "Segmentação de palavras / construção do SEA",
                "description": (
                    "Segmentar, oralmente, palavras em sílabas em situações significativas de leitura, "
                    "como cantigas e parlendas do repertório local e nacional."
                ),
                "curriculum_notes": "Currículo PE — segmentação em situações significativas, não exercícios descontextualizados.",
                "activities": (
                    "Bater palmas nas sílabas de parlendas\n"
                    "Compor e decompor nomes da turma\n"
                    "Jogos de análise fonológica com cantigas"
                ),
            },
            {
                "dim_code": "alfabetico",
                "dim_name": "Sistema de escrita alfabética",
                "practice_axis": "Análise linguística/semiótica (Alfabetização)",
                "skill_code": "EF01LP05PE",
                "bncc_code": "EF01LP05PE",
                "name": "Reconhecer a escrita alfabética como representação dos sons da fala",
                "knowledge_object": "Construção do sistema alfabético",
                "description": (
                    "Reconhecer o sistema de escrita alfabética como representação dos sons da fala, "
                    "explorando textos de tradição oral, listas e repertório local."
                ),
                "curriculum_notes": (
                    "Currículo PE / alfabetizar letrando: a escrita não é código a memorizar, "
                    "mas sistema notacional a compreender em práticas reais de linguagem."
                ),
                "activities": (
                    "Exploração de listas e crachás\n"
                    "Comparação reflexiva entre palavras\n"
                    "Bingo de letras em textos conhecidos"
                ),
            },
        ]

        skills = {}
        template_titles = {
            "rimas": ("Jogo das Rimas", 10),
            "segmentacao": ("Palmas nas Sílabas", 15),
            "oralidade": ("Roda de reconto", 15),
        }

        for i, spec in enumerate(skill_specs):
            dim, _ = DevelopmentDimension.objects.update_or_create(
                matrix_version=version,
                code=spec["dim_code"],
                defaults={
                    "name": spec["dim_name"],
                    "description": spec["curriculum_notes"],
                    "practice_axis": spec["practice_axis"],
                    "order": i,
                },
            )
            skill, _ = Skill.objects.update_or_create(
                dimension=dim,
                code=spec["skill_code"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "bncc_code": spec["bncc_code"],
                    "knowledge_object": spec["knowledge_object"],
                    "curriculum_notes": spec["curriculum_notes"],
                    "order": 0,
                },
            )
            skills[spec["dim_code"]] = skill
            title, minutes = template_titles.get(spec["dim_code"], (f"Intervenção — {spec['dim_name']}", 15))
            InterventionTemplate.objects.filter(skill=skill).exclude(title=title).update(is_active=False)
            InterventionTemplate.objects.update_or_create(
                skill=skill,
                title=title,
                defaults={
                    "objective": (
                        f"Fortalecer “{spec['name']}” em práticas de linguagem significativas, "
                        "na perspectiva de alfabetizar letrando (Currículo PE)."
                    ),
                    "suggested_activities": spec["activities"],
                    "suggested_duration_days": 14,
                    "suggested_activity_minutes": minutes,
                    "notes": f"Referência curricular: {spec['bncc_code']}",
                    "is_active": True,
                },
            )

        # Progressão conceitual alinhada ao PE: oralidade → escuta → consciência fonológica → rimas → segmentação → SEA
        progression = [
            ("oralidade", "compreensao_oral", "Da oralidade à escuta/compreensão"),
            ("compreensao_oral", "vocabulario", "Ampliação lexical em uso"),
            ("vocabulario", "consciencia_fonologica", "Da palavra ao jogo sonoro"),
            ("consciencia_fonologica", "rimas", "Jogos sonoros e tradição oral"),
            ("rimas", "segmentacao", "Rimas → segmentação silábica"),
            ("segmentacao", "alfabetico", "Segmentação → sistema alfabético"),
        ]
        for order, (a, b, notes) in enumerate(progression, start=1):
            SkillProgression.objects.update_or_create(
                from_skill=skills[a],
                to_skill=skills[b],
                defaults={"order": order, "notes": notes},
            )

        instruments = {}
        inst, _ = AssessmentInstrument.objects.update_or_create(
            matrix_version=version,
            skill=skills["rimas"],
            title="Sondagem lúdica de rimas (tradição oral)",
            defaults={
                "description": (
                    "Sondagem demonstrativa alinhada a EF12LP07PE: reconhecer rimas em "
                    "situações próximas a cantigas e parlendas. Não é treino fônico isolado."
                ),
                "instrument_type": AssessmentInstrument.InstrumentType.DIGITAL,
                "is_published": True,
                "is_active": True,
            },
        )
        # Also keep lookup by short key used elsewhere
        AssessmentInstrument.objects.filter(title="Sondagem de rimas").update(is_published=False, is_active=False)
        instruments["rimas"] = inst
        self._build_digital_items(inst, prompt_prefix="Na parlenda, qual palavra rima com")
        self._scoring(inst, skills["rimas"])

        obs, _ = AssessmentInstrument.objects.update_or_create(
            matrix_version=version,
            skill=skills["oralidade"],
            title="Sondagem observacional — reconto oral (EF15LP19PE)",
            defaults={
                "description": (
                    "Observação pedagógica: a criança reconta oralmente história, cantiga ou parlenda "
                    "ouvida (Currículo PE — EF15LP19PE)."
                ),
                "instrument_type": AssessmentInstrument.InstrumentType.OBSERVATIONAL,
                "is_published": True,
                "is_active": True,
            },
        )
        AssessmentInstrument.objects.filter(title="Sondagem observacional — linguagem oral").update(
            is_published=False, is_active=False
        )
        instruments["linguagem_oral"] = obs
        instruments["oralidade"] = obs
        item, _ = AssessmentItem.objects.update_or_create(
            instrument=obs,
            order=1,
            defaults={
                "item_type": AssessmentItem.ItemType.OBSERVATION_SCALE,
                "prompt": "A criança consegue recontar oralmente uma história, cantiga ou parlenda ouvida?",
            },
        )
        for order, (label, score) in enumerate(
            [
                ("Ainda não observado", 0),
                ("Realiza com bastante apoio", 1),
                ("Realiza com algum apoio", 2),
                ("Realiza autonomamente", 3),
            ],
            start=1,
        ):
            AssessmentOption.objects.update_or_create(
                item=item, order=order, defaults={"label": label, "score_value": score, "is_correct": score == 3}
            )
        self._scoring_obs(obs, skills["oralidade"])

        seg, _ = AssessmentInstrument.objects.update_or_create(
            matrix_version=version,
            skill=skills["segmentacao"],
            title="Sondagem lúdica de segmentação silábica (EF01LP06PE)",
            defaults={
                "instrument_type": AssessmentInstrument.InstrumentType.DIGITAL,
                "is_published": True,
                "is_active": True,
                "description": (
                    "Sondagem demonstrativa alinhada a EF01LP06PE: segmentar palavras em sílabas "
                    "em situações significativas (cantigas/parlendas)."
                ),
            },
        )
        AssessmentInstrument.objects.filter(title="Sondagem de segmentação silábica").update(
            is_published=False, is_active=False
        )
        instruments["segmentacao"] = seg
        self._build_syllable_items(seg)
        self._scoring(seg, skills["segmentacao"])
        return version, skills, instruments

    def _retire_legacy_curriculum(self, version, skills):
        """Remove habilidades/instrumentos antigos que quebravam o nexo dos relatórios."""
        keep_ids = [s.pk for s in skills.values()]
        obsolete_ids = list(Skill.objects.exclude(pk__in=keep_ids).values_list("pk", flat=True))
        legacy_titles = [
            "Sondagem de segmentação silábica",
            "Sondagem de rimas",
            "Sondagem observacional — linguagem oral",
        ]
        AssessmentInstrument.objects.filter(title__in=legacy_titles).update(is_published=False, is_active=False)
        AssessmentSession.objects.filter(instrument__title__in=legacy_titles).update(is_active=False)
        if obsolete_ids:
            StudentSkillStatus.objects.filter(skill_id__in=obsolete_ids).delete()
            AggregatedIndicator.objects.filter(skill_id__in=obsolete_ids).delete()
            AssessmentInstrument.objects.filter(skill_id__in=obsolete_ids).update(is_published=False, is_active=False)
            AssessmentSession.objects.filter(instrument__skill_id__in=obsolete_ids).update(is_active=False)
        MatrixVersion.objects.exclude(pk=version.pk).update(is_published=False)

    def _build_digital_items(self, instrument, prompt_prefix="Na parlenda, qual palavra rima com"):
        words = [
            ("GAT", "PATO", "MESA", "PATO"),
            ("SOL", "FLOR", "GOL", "GOL"),
            ("LUA", "RUA", "PÃO", "RUA"),
            ("FADA", "CASA", "LATA", "CASA"),
            ("BOI", "ROI", "PÉ", "ROI"),
        ]
        for i, (stem, a, b, correct) in enumerate(words, start=1):
            item, _ = AssessmentItem.objects.update_or_create(
                instrument=instrument,
                order=i,
                defaults={
                    "item_type": AssessmentItem.ItemType.SINGLE_SELECT,
                    "prompt": f"{prompt_prefix} {stem}?",
                    "code": f"RIM-{i:03d}",
                    "prompt_image_alt": f"Ilustração relacionada à palavra {stem}",
                },
            )
            for order, label in enumerate([a, b], start=1):
                AssessmentOption.objects.update_or_create(
                    item=item,
                    order=order,
                    defaults={
                        "label": label,
                        "score_value": 1 if label == correct else 0,
                        "is_correct": label == correct,
                    },
                )

    def _build_syllable_items(self, instrument):
        """Sondagem de segmentação oral em palavras do cotidiano (EF01LP06PE)."""
        items = [
            ("CASA", "2", "3"),
            ("SOL", "1", "2"),
            ("JANELA", "3", "2"),
            ("PATO", "2", "1"),
            ("BORBOLETA", "4", "3"),
        ]
        for i, (word, correct, wrong) in enumerate(items, start=1):
            item, _ = AssessmentItem.objects.update_or_create(
                instrument=instrument,
                order=i,
                defaults={
                    "item_type": AssessmentItem.ItemType.SINGLE_SELECT,
                    "prompt": f"Batendo palmas como na parlenda, em quantas sílabas você ouve a palavra {word}?",
                },
            )
            for order, label in enumerate([correct, wrong], start=1):
                AssessmentOption.objects.update_or_create(
                    item=item,
                    order=order,
                    defaults={
                        "label": f"{label} sílaba(s)",
                        "score_value": 1 if label == correct else 0,
                        "is_correct": label == correct,
                    },
                )

    def _scoring(self, instrument, skill):
        bands = [
            (0, 2, "needs_support", "Necessita maior mediação", True),
            (3, 4, "developing", "Em desenvolvimento", False),
            (5, 5, "demonstrated", "Habilidade demonstrada", False),
        ]
        template = InterventionTemplate.objects.filter(skill=skill).first()
        for mn, mx, code, label, attention in bands:
            rule, _ = ScoringRule.objects.update_or_create(
                instrument=instrument,
                skill=skill,
                min_score=mn,
                max_score=mx,
                defaults={"result_code": code, "status_code": code, "label": label},
            )
            SkillResultMapping.objects.update_or_create(
                scoring_rule=rule,
                defaults={
                    "needs_attention": attention,
                    "intervention_template": template if attention or code == "developing" else None,
                },
            )

    def _scoring_obs(self, instrument, skill):
        bands = [
            (0, 0, "not_observed", "Não observado", True),
            (1, 1, "needs_support", "Necessita maior mediação", True),
            (2, 2, "developing_with_support", "Desenvolvendo com apoio", False),
            (3, 3, "demonstrated", "Habilidade demonstrada", False),
        ]
        template = InterventionTemplate.objects.filter(skill=skill).first()
        for mn, mx, code, label, attention in bands:
            rule, _ = ScoringRule.objects.update_or_create(
                instrument=instrument,
                skill=skill,
                min_score=mn,
                max_score=mx,
                defaults={"result_code": code, "status_code": code, "label": label},
            )
            SkillResultMapping.objects.update_or_create(
                scoring_rule=rule,
                defaults={"needs_attention": attention, "intervention_template": template if attention else None},
            )

    def _accessibility(self, users, students, year_2026, instruments):
        features = ensure_default_features()
        # Functional profiles (A–E) — needs, not diagnoses
        demos = [
            (0, ["VISUAL_LARGE_TEXT", "VISUAL_HIGH_CONTRAST"], "Texto ampliado e alto contraste em atividades."),
            (1, ["MOTOR_NO_DRAG", "MOTOR_LARGE_TARGET"], "Evitar arrastar; usar seleção e alvos amplos."),
            (2, ["VISUAL_SCREEN_READER"], "Priorizar conteúdo legível por leitor de tela."),
            (3, ["SENSORY_REDUCED_STIMULUS", "COGNITIVE_STEP_BY_STEP"], "Reduzir estímulos; instruções passo a passo."),
            (4, ["AUDITORY_CAPTIONS", "AUDITORY_VISUAL_INSTRUCTION"], "Legendas e instrução visual quando houver áudio."),
        ]
        aee = users["aee"]
        for idx, codes, notes in demos:
            student = students[idx]
            set_student_features(student=student, feature_codes=codes, actor=aee, notes=notes)
            plan, _ = StudentSupportPlan.objects.update_or_create(
                student=student,
                school_year=year_2026,
                defaults={
                    "status": StudentSupportPlan.Status.ACTIVE,
                    "start_date": date(2026, 2, 1),
                    "notes": "Plano de apoio pedagógico (não clínico).",
                    "created_by": aee,
                },
            )
            plan.responsible_users.set([aee, users["professor"], users["coordenador"]])
            plan.strategies.all().delete()
            for code in codes:
                StudentSupportStrategy.objects.create(
                    support_plan=plan,
                    accessibility_feature=features[code],
                    strategy=f"Garantir {features[code].name} nas atividades e avaliações.",
                )

        # Item requirements + published variants for rimas instrument (pitch demo)
        rimas = instruments["rimas"]
        items = list(rimas.items.order_by("order"))
        if len(items) >= 2:
            # Item 1: accessible standard (supports screen reader)
            ItemAccessRequirement.objects.update_or_create(
                item=items[0],
                code=ItemAccessRequirement.RequirementCode.SUPPORTS_SCREEN_READER,
                defaults={"is_required": False},
            )
            ItemAccessRequirement.objects.update_or_create(
                item=items[0],
                code=ItemAccessRequirement.RequirementCode.SUPPORTS_KEYBOARD,
                defaults={"is_required": False},
            )
            # Item 2: visual+drag — incompatible without variant
            ItemAccessRequirement.objects.update_or_create(
                item=items[1],
                code=ItemAccessRequirement.RequirementCode.REQUIRES_VISION,
                defaults={"is_required": True},
            )
            ItemAccessRequirement.objects.update_or_create(
                item=items[1],
                code=ItemAccessRequirement.RequirementCode.REQUIRES_DRAG,
                defaults={"is_required": True},
            )
            items[1].item_type = AssessmentItem.ItemType.IMAGE_SELECT
            items[1].prompt = "Arraste a palavra que rima com SOL até a imagem correta."
            items[1].save(update_fields=["item_type", "prompt", "updated_at"])

            low_vision, _ = AssessmentItemVariant.objects.update_or_create(
                parent_item=items[1],
                name="LowVision",
                version=1,
                defaults={
                    "instruction_text": "Qual palavra rima com SOL? Texto ampliado.",
                    "equivalence_status": AssessmentItemVariant.EquivalenceStatus.EQUIVALENT,
                    "adaptation_type": AssessmentItemVariant.AdaptationType.ACCESS_ACCOMMODATION,
                    "pedagogical_approval_status": AssessmentItemVariant.ApprovalStatus.PUBLISHED,
                    "equivalence_notes": "Mesma habilidade de rima; muda apenas apresentação.",
                    "active": True,
                    "proposed_by": users["coordenador"],
                    "approved_by": users["coordenador"],
                },
            )
            low_vision.supported_features.set(
                [features["VISUAL_LARGE_TEXT"], features["VISUAL_HIGH_CONTRAST"], features["VISUAL_SCREEN_READER"]]
            )

            no_drag, _ = AssessmentItemVariant.objects.update_or_create(
                parent_item=items[1],
                name="NoDrag",
                version=1,
                defaults={
                    "instruction_text": "Selecione a palavra que rima com SOL (sem arrastar).",
                    "item_type_override": AssessmentItem.ItemType.SELECT_THEN_MATCH,
                    "equivalence_status": AssessmentItemVariant.EquivalenceStatus.EQUIVALENT,
                    "adaptation_type": AssessmentItemVariant.AdaptationType.ACCESS_ACCOMMODATION,
                    "pedagogical_approval_status": AssessmentItemVariant.ApprovalStatus.PUBLISHED,
                    "equivalence_notes": "Associação palavra-imagem preservada via seleção.",
                    "active": True,
                    "proposed_by": aee,
                    "approved_by": users["coordenador"],
                },
            )
            no_drag.supported_features.set([features["MOTOR_NO_DRAG"], features["MOTOR_LARGE_TARGET"], features["MOTOR_KEYBOARD"]])

            # Item 3: exclusively visual for screen-reader demo (no equivalent unless alt)
            if len(items) >= 3:
                ItemAccessRequirement.objects.update_or_create(
                    item=items[2],
                    code=ItemAccessRequirement.RequirementCode.REQUIRES_VISION,
                    defaults={"is_required": True},
                )
                screen_reader_var, _ = AssessmentItemVariant.objects.update_or_create(
                    parent_item=items[2],
                    name="ScreenReader",
                    version=1,
                    defaults={
                        "instruction_text": "Qual palavra rima com LUA? Ouça ou leia as alternativas.",
                        "equivalence_status": AssessmentItemVariant.EquivalenceStatus.EQUIVALENT,
                        "adaptation_type": AssessmentItemVariant.AdaptationType.ACCESS_ACCOMMODATION,
                        "pedagogical_approval_status": AssessmentItemVariant.ApprovalStatus.PUBLISHED,
                        "active": True,
                        "approved_by": users["coordenador"],
                    },
                )
                screen_reader_var.supported_features.set([features["VISUAL_SCREEN_READER"]])
                ItemAccessRequirement.objects.update_or_create(
                    item=items[2],
                    code=ItemAccessRequirement.RequirementCode.SUPPORTS_SCREEN_READER,
                    defaults={"is_required": False, "notes": "Suporte via variante ScreenReader"},
                )

    def _sessions(self, teacher, teacher2, students, classrooms, instruments, skills):
        # Longitudinal 2025 first, so the 2026 status remains the current snapshot.
        luna = students[0]
        luna_2025 = Enrollment.objects.filter(student=luna, school_year__year=2025).first()
        if luna_2025:
            self._complete_with_score(teacher, luna_2025, instruments["rimas"], correct=3)
        # Coherent network story: every 2026 classroom has assessments feeding dashboards.
        self._seed_infantil_va_journey(teacher, classrooms[0], students, instruments, skills)
        # c1 Maria Inez V B — acompanhamento regular (não competir com a jornada da V A)
        for enrollment in classrooms[1].enrollments.filter(is_active=True):
            self._complete_with_score(teacher, enrollment, instruments["rimas"], correct=4)
            self._complete_with_score(teacher, enrollment, instruments["oralidade"], correct=3)
        # c2 Tia Noêmia V A — fragmentação na segmentação (Alice)
        for enrollment in classrooms[2].enrollments.filter(is_active=True):
            self._complete_with_score(teacher2, enrollment, instruments["segmentacao"], correct=0)
            self._complete_with_score(teacher2, enrollment, instruments["rimas"], correct=2)
        # c3 Albino Moreira 1º A — em desenvolvimento (Benício)
        for enrollment in classrooms[3].enrollments.filter(is_active=True):
            self._complete_with_score(teacher2, enrollment, instruments["rimas"], correct=3)
            self._complete_with_score(teacher2, enrollment, instruments["oralidade"], correct=2)
        # c4 Eliel Peixoto IV A — misto (Helena)
        for enrollment in classrooms[4].enrollments.filter(is_active=True):
            self._complete_with_score(teacher, enrollment, instruments["rimas"], correct=4)
            self._complete_with_score(teacher, enrollment, instruments["oralidade"], correct=2)
        # c5 Ananias Crisóstomo V A — regular
        for enrollment in classrooms[5].enrollments.filter(is_active=True):
            self._complete_with_score(teacher, enrollment, instruments["rimas"], correct=4)
            self._complete_with_score(teacher, enrollment, instruments["oralidade"], correct=3)

        self._demo_followup(teacher, students, classrooms, skills)

    def _seed_infantil_va_journey(self, teacher, classroom, students, instruments, skills):
        student_ids = list(
            classroom.enrollments.filter(is_active=True, status=Enrollment.Status.ACTIVE).values_list(
                "student_id", flat=True
            )
        )
        StudentSkillStatus.objects.filter(student_id__in=student_ids, enrollment__classroom=classroom).delete()
        StudentSkillStatus.objects.filter(student_id__in=student_ids, enrollment__school_year__is_active=True).delete()
        StudentIntervention.objects.filter(
            enrollment__classroom=classroom,
            status__in=[InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS],
        ).update(status=InterventionStatus.CANCELLED, is_active=False)
        AssessmentSession.objects.filter(enrollment__classroom=classroom, is_active=True).update(is_active=False)

        by_name = {student.full_name: student for student in students}
        rimas = instruments["rimas"]
        seg = instruments["segmentacao"]
        oral = instruments["oralidade"]

        def enrollment_of(name):
            student = by_name[name]
            return student.enrollments.filter(classroom=classroom, is_active=True).first() or student.current_enrollment()

        for name in ["Luna Ferreira", "Theo Martins", "Laura Mendes", "Noah Barbosa", "Valentina Costa"]:
            enrollment = enrollment_of(name)
            if enrollment:
                self._complete_with_score(teacher, enrollment, rimas, correct=1)
        for name in ["Theo Martins", "Noah Barbosa", "Valentina Costa"]:
            enrollment = enrollment_of(name)
            if enrollment:
                self._complete_with_score(teacher, enrollment, seg, correct=1)
        for name in ["Luna Ferreira", "Laura Mendes", "Bernardo Teixeira"]:
            enrollment = enrollment_of(name)
            if enrollment:
                self._complete_with_score(teacher, enrollment, oral, correct=3)
        bernardo = enrollment_of("Bernardo Teixeira")
        if bernardo:
            self._complete_with_score(teacher, bernardo, rimas, correct=4)
        manuela = enrollment_of("Manuela Alves")
        if manuela:
            rimas_session = self._complete_with_score(teacher, manuela, rimas, correct=1)
            past_session = timezone.now() - timedelta(days=20)
            AssessmentSession.objects.filter(pk=rimas_session.pk).update(
                started_at=past_session,
                completed_at=past_session,
            )
            self._complete_with_score(teacher, manuela, oral, correct=3)
        maya = enrollment_of("Maya Duarte")
        if maya:
            self._complete_with_score(teacher, maya, oral, correct=1)
            self._complete_with_score(teacher, maya, rimas, correct=4)
        # Arthur Lima: sem sessão — sondagem pendente

    def _demo_followup(self, teacher, students, classrooms, skills):
        template_rimas = InterventionTemplate.objects.filter(skill=skills["rimas"], is_active=True).first()
        template_seg = InterventionTemplate.objects.filter(skill=skills["segmentacao"], is_active=True).first()
        template_oral = InterventionTemplate.objects.filter(skill=skills["oralidade"], is_active=True).first()
        by_name = {student.full_name: student for student in students}
        past = timezone.now() - timedelta(days=10)

        maya = by_name.get("Maya Duarte")
        if maya and template_oral:
            enrollment = maya.current_enrollment()
            ci, _ = ClassroomIntervention.objects.update_or_create(
                classroom=enrollment.classroom,
                skill=skills["oralidade"],
                defaults={
                    "template": template_oral,
                    "responsible": teacher,
                    "objective": template_oral.objective,
                    "activities": template_oral.suggested_activities,
                    "starts_on": date.today() - timedelta(days=1),
                    "status": InterventionStatus.IN_PROGRESS,
                    "is_active": True,
                },
            )
            StudentIntervention.objects.update_or_create(
                student=maya,
                enrollment=enrollment,
                skill=skills["oralidade"],
                defaults={
                    "classroom_intervention": ci,
                    "template": template_oral,
                    "responsible": teacher,
                    "objective": template_oral.objective,
                    "activities": template_oral.suggested_activities,
                    "starts_on": date.today() - timedelta(days=1),
                    "status": InterventionStatus.IN_PROGRESS,
                    "followup_result": "",
                    "followup_recorded_at": None,
                    "is_active": True,
                },
            )
            Evidence.objects.get_or_create(
                student=maya,
                enrollment=enrollment,
                recorded_by=teacher,
                description="Roda de reconto iniciada; registro de acompanhamento ainda pendente.",
                defaults={"skill": skills["oralidade"], "file_type": Evidence.FileType.TEXT},
            )

        manuela = by_name.get("Manuela Alves")
        if manuela and template_rimas:
            enrollment = manuela.current_enrollment()
            iv, _ = StudentIntervention.objects.update_or_create(
                student=manuela,
                enrollment=enrollment,
                skill=skills["rimas"],
                defaults={
                    "template": template_rimas,
                    "responsible": teacher,
                    "objective": template_rimas.objective,
                    "activities": template_rimas.suggested_activities,
                    "starts_on": date.today() - timedelta(days=14),
                    "ends_on": date.today() - timedelta(days=7),
                    "status": InterventionStatus.COMPLETED,
                    "followup_result": FollowupResult.PROGRESSED,
                    "followup_recorded_at": past,
                    "observation": "Participou da atividade Jogo das Rimas em grupo. Apresentou avanço durante a atividade.",
                    "is_active": True,
                    "classroom_intervention": None,
                },
            )
            StudentIntervention.objects.filter(pk=iv.pk).update(
                created_at=past - timedelta(days=4),
                updated_at=past,
                followup_recorded_at=past,
            )
            Evidence.objects.get_or_create(
                student=manuela,
                enrollment=enrollment,
                recorded_by=teacher,
                description="Participou da atividade Jogo das Rimas em grupo. Apresentou avanço durante a atividade.",
                defaults={"skill": skills["rimas"], "file_type": Evidence.FileType.TEXT, "visible_to_family": False},
            )

        # Cancel stale open rimas/segmentation interventions in V A that would hide the suggested groups.
        va = classrooms[0]
        StudentIntervention.objects.filter(
            enrollment__classroom=va,
            skill__in=[skills["rimas"], skills["segmentacao"]],
            status__in=[InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS],
        ).exclude(student__full_name="Manuela Alves").update(status=InterventionStatus.CANCELLED, is_active=False)

        # Evitar fila ruidosa na V B (turma secundária da professora).
        ClassroomIntervention.objects.filter(
            classroom=classrooms[1],
            status__in=[InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS],
        ).update(status=InterventionStatus.COMPLETED)
        StudentIntervention.objects.filter(
            enrollment__classroom=classrooms[1],
            status__in=[InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS],
        ).update(status=InterventionStatus.COMPLETED, followup_result=FollowupResult.PROGRESSED)

        if template_seg:
            ClassroomIntervention.objects.update_or_create(
                classroom=classrooms[2],
                skill=skills["segmentacao"],
                defaults={
                    "template": template_seg,
                    "responsible": teacher,
                    "objective": "Segmentar palavras em sílabas em cantigas conhecidas.",
                    "activities": template_seg.suggested_activities,
                    "starts_on": date.today(),
                    "status": InterventionStatus.PLANNED,
                    "is_active": True,
                },
            )

    def _family_and_adoption(self, users, students):
        luna = students[0]
        FamilyLink.objects.update_or_create(
            user=users["familia"],
            student=luna,
            defaults={"kinship": FamilyLink.Kinship.MOTHER, "is_active": True},
        )
        Evidence.objects.filter(student=luna, is_active=True).update(visible_to_family=True)
        ensure_formation_catalog()

    def _complete_with_score(self, teacher, enrollment, instrument, correct: int):
        AssessmentSession.objects.filter(
            enrollment=enrollment, instrument__skill=instrument.skill, is_active=True
        ).update(is_active=False)
        AssessmentSession.objects.filter(
            enrollment=enrollment, instrument=instrument, is_active=True
        ).delete()
        session = start_session(enrollment=enrollment, instrument=instrument, started_by=teacher)
        items = list(instrument.items.order_by("order", "id"))
        for i, item in enumerate(items):
            options = list(item.options.order_by("order"))
            if not options:
                save_response(
                    session=session,
                    item=item,
                    applied_by=teacher,
                    text_value="Observação demonstrativa.",
                    is_observational=True,
                )
                continue
            if instrument.instrument_type == AssessmentInstrument.InstrumentType.OBSERVATIONAL:
                option = options[min(correct, len(options) - 1)]
            else:
                correct_opt = next((o for o in options if o.is_correct), options[0])
                wrong_opt = next((o for o in options if not o.is_correct), options[-1])
                option = correct_opt if i < correct else wrong_opt
            save_response(session=session, item=item, option=option, applied_by=teacher)
        complete_session(session)
        return session
