"""Curriculum alignment views (Currículo de Pernambuco)."""
from django.shortcuts import render
from django.views import View

from apps.core.permissions import ManagementRequiredMixin
from apps.curriculum.models import DevelopmentDimension, MatrixVersion, PedagogicalMatrix, Skill, SkillProgression


class CurriculumAlignmentView(ManagementRequiredMixin, View):
    """Exibe o alinhamento da matriz ao Currículo de Pernambuco / BNCC."""

    def get(self, request):
        version = (
            MatrixVersion.objects.filter(is_published=True)
            .select_related("matrix")
            .order_by("-published_at", "-id")
            .first()
        )
        dimensions = []
        progressions = []
        if version:
            dimensions = (
                DevelopmentDimension.objects.filter(matrix_version=version)
                .prefetch_related("skills")
                .order_by("order")
            )
            progressions = SkillProgression.objects.filter(
                from_skill__dimension__matrix_version=version
            ).select_related("from_skill", "to_skill").order_by("order")
        return render(
            request,
            "admin_panel/curriculum_alignment.html",
            {
                "version": version,
                "dimensions": dimensions,
                "progressions": progressions,
                "principles": [
                    {
                        "title": "Alfabetizar letrando",
                        "text": (
                            "O Currículo de Pernambuco assume alfabetizar e letrar simultaneamente: "
                            "apropriar-se do sistema de escrita em práticas reais de leitura e escrita "
                            "(Soares), sem reduzir o trabalho a decodificar/codificar isoladamente."
                        ),
                    },
                    {
                        "title": "Consciência fonológica em contexto",
                        "text": (
                            "A consciência fonológica é compreendida como capacidade metalinguística "
                            "(frases → palavras → sílabas → fonemas), sempre vinculada a usos da língua "
                            "— parlendas, cantigas, listas —, e não a treino fônico sem textos."
                        ),
                    },
                    {
                        "title": "Transição Educação Infantil → Anos Iniciais",
                        "text": (
                            "Valorizar aprendizagens anteriores, o caráter lúdico e a continuidade do "
                            "percurso, com ênfase na alfabetização nos 1º e 2º anos associada ao letramento."
                        ),
                    },
                    {
                        "title": "Texto e gêneros do cotidiano",
                        "text": (
                            "O texto é centro das práticas. Gêneros da vida cotidiana e da tradição oral "
                            "(bilhetes, listas, cantigas, parlendas, cordéis) orientam sondagens e intervenções."
                        ),
                    },
                ],
            },
        )
