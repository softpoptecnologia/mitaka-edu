from django.urls import path

from apps.accounts import views_management as views
from apps.accounts import views_teachers as teacher_views
from apps.assessments import views_author as instrument_views
from apps.curriculum import views as curriculum_views
from apps.curriculum import views_write as curriculum_write
from apps.interventions import views as intervention_views
from apps.reports import views as report_views
from apps.schools import views as school_views
from apps.students import views as student_views

app_name = "management"

urlpatterns = [
    path("", views.ManagementDashboardView.as_view(), name="dashboard"),
    path("municipios/", school_views.MunicipalityListView.as_view(), name="municipalities"),
    path("municipios/novo/", school_views.MunicipalityCreateView.as_view(), name="municipality_create"),
    path("municipios/<int:pk>/editar/", school_views.MunicipalityUpdateView.as_view(), name="municipality_update"),
    path("escolas/", views.SchoolListView.as_view(), name="schools"),
    path("escolas/nova/", school_views.SchoolCreateView.as_view(), name="school_create"),
    path("escolas/<int:pk>/editar/", school_views.SchoolUpdateView.as_view(), name="school_update"),
    path("escolas/<int:pk>/desativar/", school_views.SchoolArchiveView.as_view(), name="school_archive"),
    path("escolas/<int:pk>/excluir/", school_views.SchoolDeleteView.as_view(), name="school_delete"),
    path("turmas/", views.ClassroomListView.as_view(), name="classrooms"),
    path("turmas/nova/", school_views.ClassroomCreateView.as_view(), name="classroom_create"),
    path("turmas/<int:pk>/editar/", school_views.ClassroomUpdateView.as_view(), name="classroom_update"),
    path("turmas/<int:pk>/desativar/", school_views.ClassroomArchiveView.as_view(), name="classroom_archive"),
    path("turmas/<int:pk>/excluir/", school_views.ClassroomDeleteView.as_view(), name="classroom_delete"),
    path("estudantes/", views.StudentListView.as_view(), name="students"),
    path("estudantes/novo/", student_views.StudentCreateView.as_view(), name="student_create"),
    path("estudantes/<int:pk>/editar/", student_views.StudentUpdateView.as_view(), name="student_update"),
    path("estudantes/<int:pk>/desativar/", student_views.StudentArchiveView.as_view(), name="student_archive"),
    path("estudantes/<int:pk>/excluir/", student_views.StudentDeleteView.as_view(), name="student_delete"),
    path("matriculas/", views.EnrollmentListView.as_view(), name="enrollments"),
    path("matriculas/nova/", student_views.EnrollmentCreateView.as_view(), name="enrollment_create"),
    path("matriculas/<int:pk>/editar/", student_views.EnrollmentUpdateView.as_view(), name="enrollment_update"),
    path("matriculas/<int:pk>/desativar/", student_views.EnrollmentArchiveView.as_view(), name="enrollment_archive"),
    path("matriculas/<int:pk>/excluir/", student_views.EnrollmentDeleteView.as_view(), name="enrollment_delete"),
    path("matriculas/importar/", views.ImportStudentsView.as_view(), name="import_students"),
    path("professores/", views.TeacherListView.as_view(), name="teachers"),
    path("professores/novo/", teacher_views.TeacherCreateView.as_view(), name="teacher_create"),
    path("professores/<int:pk>/editar/", teacher_views.TeacherUpdateView.as_view(), name="teacher_update"),
    path("professores/<int:pk>/desativar/", teacher_views.TeacherArchiveView.as_view(), name="teacher_archive"),
    path("professores/<int:pk>/excluir/", teacher_views.TeacherDeleteView.as_view(), name="teacher_delete"),
    path("professores/vincular/", teacher_views.TeacherLinkCreateView.as_view(), name="teacher_link_create"),
    path("professores/vinculo/<int:pk>/excluir/", teacher_views.TeacherLinkDeleteView.as_view(), name="teacher_link_delete"),
    path("matriz/", views.MatrixListView.as_view(), name="matrix"),
    path("matriz/nova/", curriculum_write.MatrixCreateView.as_view(), name="matrix_create"),
    path("matriz/<int:pk>/editar/", curriculum_write.MatrixUpdateView.as_view(), name="matrix_update"),
    path("matriz/versao/nova/", curriculum_write.MatrixVersionCreateView.as_view(), name="matrix_version_create"),
    path("matriz/versao/<int:pk>/publicar/", curriculum_write.MatrixVersionPublishView.as_view(), name="matrix_version_publish"),
    path("dimensoes/", views.DimensionsSkillsView.as_view(), name="dimensions"),
    path("dimensoes/nova/", curriculum_write.DimensionCreateView.as_view(), name="dimension_create"),
    path("dimensoes/<int:pk>/editar/", curriculum_write.DimensionUpdateView.as_view(), name="dimension_update"),
    path("habilidades/nova/", curriculum_write.SkillCreateView.as_view(), name="skill_create"),
    path("habilidades/<int:pk>/editar/", curriculum_write.SkillUpdateView.as_view(), name="skill_update"),
    path("alinhamento-curricular/", curriculum_views.CurriculumAlignmentView.as_view(), name="curriculum_alignment"),
    path("instrumentos/", views.InstrumentListView.as_view(), name="instruments"),
    path("instrumentos/novo/", instrument_views.InstrumentCreateView.as_view(), name="instrument_create"),
    path("instrumentos/<int:pk>/editar/", instrument_views.InstrumentUpdateView.as_view(), name="instrument_update"),
    path("instrumentos/<int:pk>/itens/", instrument_views.InstrumentItemsView.as_view(), name="instrument_items"),
    path("instrumentos/<int:pk>/itens/<int:item_id>/excluir/", instrument_views.InstrumentItemDeleteView.as_view(), name="instrument_item_delete"),
    path("instrumentos/<int:pk>/desativar/", instrument_views.InstrumentArchiveView.as_view(), name="instrument_archive"),
    path("templates/", intervention_views.TemplateListView.as_view(), name="intervention_templates"),
    path("templates/novo/", intervention_views.TemplateCreateView.as_view(), name="intervention_template_create"),
    path("templates/<int:pk>/editar/", intervention_views.TemplateUpdateView.as_view(), name="intervention_template_update"),
    path("templates/<int:pk>/desativar/", intervention_views.TemplateArchiveView.as_view(), name="intervention_template_archive"),
    path("indicadores/", views.IndicatorsView.as_view(), name="indicators"),
    path("intervencoes/", views.InterventionsListView.as_view(), name="interventions"),
    path("anos-letivos/novo/", views.NewSchoolYearView.as_view(), name="new_year"),
    path("anos-letivos/<int:pk>/editar/", school_views.SchoolYearUpdateView.as_view(), name="school_year_update"),
    path("anos-letivos/<int:pk>/ativar/", school_views.SchoolYearActivateView.as_view(), name="school_year_activate"),
    path("relatorios/", report_views.ReportIndexView.as_view(), name="reports"),
    path("relatorios/estudante/<int:pk>/", report_views.StudentReportView.as_view(), name="report_student"),
    path("relatorios/turma/<int:pk>/", report_views.ClassroomReportView.as_view(), name="report_classroom"),
    path("relatorios/escola/<int:pk>/", report_views.SchoolReportView.as_view(), name="report_school"),
    path("relatorios/rede/", report_views.NetworkReportView.as_view(), name="report_network"),
]
