"""Standard Mitaka Edu PDF layout for pedagogical reports."""
from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAL = colors.HexColor("#00796b")
INK = colors.HexColor("#0d1b2a")
MUTED = colors.HexColor("#5c6b7a")
LINE = colors.HexColor("#e4e8ee")
HEADER_BG = colors.HexColor("#f7f9fb")
WHITE = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "MitakaBrand",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "MitakaTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=INK,
            spaceAfter=3,
            leading=19,
        ),
        "subtitle": ParagraphStyle(
            "MitakaSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=INK,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "MitakaMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "MitakaH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=INK,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "MitakaBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=INK,
            leading=12,
            spaceAfter=4,
        ),
        "note": ParagraphStyle(
            "MitakaNote",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=MUTED,
            leading=11,
            spaceBefore=8,
        ),
        "th": ParagraphStyle(
            "MitakaTh",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=INK,
            leading=11,
        ),
        "td": ParagraphStyle(
            "MitakaTd",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=INK,
            leading=11,
        ),
        "footer": ParagraphStyle(
            "MitakaFooter",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }


class MitakaPdfBuilder:
    """Shared visual pattern: header, sections, tables, pedagogical footer."""

    def __init__(self, *, title: str, subtitle: str = "", meta: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.meta = meta
        self.styles = _styles()
        self.story: list = []
        self._header()

    def _header(self):
        s = self.styles
        self.story.append(Paragraph("MITAKA EDU · Evidências que transformam aprendizagens", s["brand"]))
        self.story.append(Paragraph(self.title, s["title"]))
        if self.subtitle:
            self.story.append(Paragraph(self.subtitle, s["subtitle"]))
        generated = timezone.localtime().strftime("%d/%m/%Y %H:%M")
        meta = self.meta or f"Documento pedagógico · gerado em {generated}"
        if "gerado" not in meta.lower():
            meta = f"{meta} · Gerado em {generated}"
        self.story.append(Paragraph(meta, s["meta"]))
        self.story.append(HRFlowable(width="100%", thickness=0.6, color=INK, spaceAfter=10))

    def section(self, heading: str):
        self.story.append(Paragraph(heading, self.styles["h2"]))

    def paragraph(self, text: str):
        if text:
            self.story.append(Paragraph(str(text), self.styles["body"]))

    def kv_grid(self, pairs: list[tuple[str, str]], cols: int = 2):
        s = self.styles
        cells = []
        row = []
        for label, value in pairs:
            row.append(Paragraph(f"<b>{label}</b><br/>{value or '—'}", s["td"]))
            if len(row) == cols:
                cells.append(row)
                row = []
        if row:
            while len(row) < cols:
                row.append("")
            cells.append(row)
        if not cells:
            return
        table = Table(cells, colWidths=[8.5 * cm] * cols)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
                    ("BOX", (0, 0), (-1, -1), 0.3, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        self.story.append(table)
        self.story.append(Spacer(1, 6))

    def table(self, headers: list[str], rows: list[list], col_widths=None):
        s = self.styles
        data = [[Paragraph(h, s["th"]) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(c) if c not in (None, "") else "—", s["td"]) for c in row])
        usable = 18 * cm
        if not col_widths:
            col_widths = [usable / len(headers)] * len(headers)
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), INK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HEADER_BG]),
            ("BOX", (0, 0), (-1, -1), 0.3, LINE),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
            ("INNERGRID", (0, 1), (-1, -1), 0.2, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        table.setStyle(TableStyle(style_cmds))
        self.story.append(table)
        self.story.append(Spacer(1, 6))

    def note(self, text: str):
        self.story.append(Paragraph(text, self.styles["note"]))

    def build(self) -> bytes:
        buffer = BytesIO()

        def _footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.5)
            canvas.line(1.6 * cm, 1.45 * cm, A4[0] - 1.6 * cm, 1.45 * cm)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(MUTED)
            canvas.drawString(
                1.6 * cm,
                0.9 * cm,
                "Mitaka Edu · documento pedagógico · não constitui diagnóstico clínico",
            )
            canvas.drawRightString(A4[0] - 1.5 * cm, 0.9 * cm, f"Página {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.5 * cm,
            bottomMargin=2.1 * cm,
            title=self.title,
            author="Mitaka Edu",
        )
        doc.build(self.story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()


def build_student_pdf(data: dict) -> bytes:
    student = data["student"]
    enrollment = data.get("enrollment")
    pdf = MitakaPdfBuilder(
        title="Relatório individual do estudante",
        subtitle=student.full_name,
        meta=(
            f"Código {student.external_code or '—'} · "
            f"{enrollment.classroom.name if enrollment else 'sem matrícula ativa'} · "
            f"{enrollment.classroom.school.name if enrollment else ''}"
        ),
    )
    pdf.kv_grid(
        [
            ("Matrícula atual", enrollment.classroom.name if enrollment else "—"),
            ("Escola", enrollment.classroom.school.name if enrollment else "—"),
            ("Ano letivo", str(enrollment.school_year) if enrollment else "—"),
            ("Sessões concluídas", str(data.get("completed_sessions", 0))),
            ("Habilidades em atenção", str(data.get("attention_count", 0))),
            ("Sessões com recurso de acesso", str(data.get("adapted_sessions", 0))),
        ]
    )
    if data.get("resource_labels"):
        pdf.section("Recursos necessários para esta criança")
        pdf.paragraph(", ".join(data["resource_labels"]))
        pdf.paragraph("Informações funcionais de acesso — sem dados clínicos.")

    pdf.section("Trajetória escolar")
    pdf.table(
        ["Ano", "Turma", "Escola", "Status"],
        [
            [
                str(e.school_year),
                e.classroom.name,
                e.classroom.school.name,
                e.get_status_display(),
            ]
            for e in data.get("trajectory", [])
        ],
        col_widths=[3 * cm, 5 * cm, 6.5 * cm, 3.5 * cm],
    )

    pdf.section("Situação por habilidade")
    pdf.table(
        ["Habilidade", "Status", "Pontuação"],
        [
            [
                st.skill.name,
                st.status_label + (" (atenção)" if st.needs_attention else ""),
                f"{st.raw_score}/{st.max_score}" if st.raw_score is not None else "—",
            ]
            for st in data.get("statuses", [])
        ],
        col_widths=[9 * cm, 5.5 * cm, 3.5 * cm],
    )

    pdf.section("Sessões de avaliação")
    pdf.table(
        ["Instrumento", "Modo", "Status", "Data"],
        [
            [
                s.instrument.title,
                s.get_application_mode_display() if s.application_mode else "Padrão",
                s.get_status_display(),
                s.started_at.strftime("%d/%m/%Y") if s.started_at else "—",
            ]
            for s in data.get("sessions", [])
        ],
        col_widths=[8 * cm, 3.5 * cm, 3.5 * cm, 3 * cm],
    )

    pdf.section("Evidências")
    if data.get("evidences"):
        pdf.table(
            ["Data", "Tipo", "Habilidade", "Descrição"],
            [
                [
                    ev.recorded_at.strftime("%d/%m/%Y") if ev.recorded_at else "—",
                    ev.get_file_type_display(),
                    ev.skill.name if ev.skill else "—",
                    (ev.description or "")[:120],
                ]
                for ev in data["evidences"]
            ],
            col_widths=[2.5 * cm, 3 * cm, 5 * cm, 7.5 * cm],
        )
    else:
        pdf.paragraph("Nenhuma evidência registrada.")

    pdf.section("Intervenções")
    if data.get("interventions"):
        pdf.table(
            ["Habilidade", "Status", "Objetivo"],
            [
                [i.skill.name, i.get_status_display(), (i.objective or "")[:140]]
                for i in data["interventions"]
            ],
            col_widths=[5 * cm, 3.5 * cm, 9.5 * cm],
        )
    else:
        pdf.paragraph("Nenhuma intervenção ativa.")

    pdf.note(
        "Acomodações de acesso não reduzem automaticamente a expectativa de aprendizagem. "
        "Barreiras de acessibilidade não devem ser lidas como baixo desempenho."
    )
    return pdf.build()


def build_classroom_pdf(data: dict) -> bytes:
    classroom = data["classroom"]
    pdf = MitakaPdfBuilder(
        title="Relatório de turma",
        subtitle=f"{classroom.name} · {classroom.grade_label}",
        meta=f"{classroom.school.name} · {classroom.school_year}",
    )
    pdf.kv_grid(
        [
            ("Estudantes", str(data.get("total", 0))),
            ("Acompanhamento regular", str(data.get("ok", 0))),
            ("Sondagem pendente", str(data.get("pending", 0))),
            ("Atenção", str(data.get("attention", 0))),
            ("Cobertura avaliativa", f"{data.get('coverage', 0)}%"),
            ("Intervenções de turma", str(len(data.get("classroom_interventions") or []))),
        ]
    )
    if data.get("skill_attention"):
        pdf.section("Habilidades com maior atenção na turma")
        pdf.table(
            ["Habilidade", "Estudantes"],
            [[name, str(count)] for name, count in data["skill_attention"]],
            col_widths=[14 * cm, 4 * cm],
        )
    pdf.section("Estudantes")
    pdf.table(
        ["#", "Nome", "Código", "Acompanhamento"],
        [
            [str(i), row["student"].full_name, row["student"].external_code or "—", row["label"]]
            for i, row in enumerate(data.get("rows", []), start=1)
        ],
        col_widths=[1.5 * cm, 8 * cm, 3.5 * cm, 5 * cm],
    )
    if data.get("classroom_interventions"):
        pdf.section("Intervenções coletivas")
        pdf.table(
            ["Habilidade", "Status", "Objetivo"],
            [
                [ci.skill.name, ci.get_status_display(), (ci.objective or "")[:140]]
                for ci in data["classroom_interventions"]
            ],
            col_widths=[5 * cm, 3.5 * cm, 9.5 * cm],
        )
    pdf.note("Relatório de acompanhamento pedagógico da turma — sem classificação clínica.")
    return pdf.build()


def build_school_pdf(data: dict) -> bytes:
    school = data["school"]
    pdf = MitakaPdfBuilder(
        title="Relatório escolar",
        subtitle=school.name,
        meta=f"Código {school.code} · {data.get('scope_label') or data.get('year') or 'ano letivo ativo'}",
    )
    pdf.kv_grid(
        [
            ("Turmas", str(data.get("classrooms_count", 0))),
            ("Estudantes", str(data.get("students_count", 0))),
            ("Estudantes em atenção", str(data.get("attention_students", 0))),
            ("Cobertura avaliativa", f"{data.get('coverage', 0)}%"),
        ]
    )
    school_indicators = data.get("school_indicators") or []
    if school_indicators:
        pdf.section("Escola — % em atenção por habilidade")
        pdf.table(
            ["Habilidade", "Código", "% em atenção", "Amostra"],
            [
                [
                    ind.skill.name if ind.skill_id else "—",
                    (ind.skill.bncc_code or ind.skill.code) if ind.skill_id else "—",
                    f"{ind.metric_value}%",
                    str(ind.sample_size),
                ]
                for ind in school_indicators
            ],
            col_widths=[8 * cm, 3.5 * cm, 3.5 * cm, 3 * cm],
        )
    classroom_indicators = data.get("classroom_indicators") or []
    if classroom_indicators:
        pdf.section("Turmas — % em atenção por habilidade")
        pdf.table(
            ["Turma", "Habilidade", "% em atenção", "Amostra"],
            [
                [
                    ind.classroom.name if ind.classroom_id else "—",
                    ind.skill.name if ind.skill_id else "—",
                    f"{ind.metric_value}%",
                    str(ind.sample_size),
                ]
                for ind in classroom_indicators
            ],
            col_widths=[4 * cm, 8 * cm, 3.5 * cm, 2.5 * cm],
        )
    if not school_indicators and not classroom_indicators:
        pdf.paragraph("Nenhum indicador disponível para este recorte.")
    pdf.note("Indicadores administrativos e pedagógicos. Não comparar grupos por condição individual.")
    return pdf.build()


def build_secretaria_pdf(data: dict) -> bytes:
    """PDF da secretaria — respeita o mesmo recorte/filtros do painel."""
    filters = data.get("filters")
    muni = data.get("municipality")
    subtitle = data.get("scope_label") or (f"{muni.name}/{muni.state}" if muni else "Rede municipal")
    pdf = MitakaPdfBuilder(
        title="Relatório da Secretaria Municipal",
        subtitle=subtitle,
        meta=f"Recorte: {data.get('recorte_label') or 'Toda a rede no recorte'}",
    )
    pdf.section("Indicadores do recorte")
    pdf.kv_grid(
        [
            ("Escolas", str(data.get("schools_count", 0))),
            ("Turmas", str(data.get("classrooms_count", 0))),
            ("Estudantes", str(data.get("students_count", 0))),
            ("Cobertura avaliativa", f"{data.get('coverage', 0)}%"),
            ("Estudantes em atenção", str(data.get("attention_students", 0))),
            ("Sessões com recurso de acesso", str((data.get("a11y_stats") or {}).get("sessions_with_accessibility", 0))),
        ]
    )
    if filters:
        pdf.paragraph(
            "Filtros aplicados: "
            + ", ".join(
                f"{label} = {value}"
                for label, value in [
                    ("ano", str(filters.year) if filters.year else None),
                    ("escola", filters.school.name if filters.school else None),
                    ("turma", filters.classroom.name if filters.classroom else None),
                    ("série", filters.grade or None),
                    ("habilidade", filters.skill.name if filters.skill else None),
                    ("recorte", filters.recorte_label()),
                ]
                if value
            )
        )
    pdf.section("Habilidades no recorte")
    skill_rows = data.get("skill_rows") or []
    if skill_rows:
        pdf.table(
            ["Habilidade", "Código", "% atenção", "Amostra"],
            [
                [r["name"], r.get("bncc_code") or "—", f"{r['pct']}%", str(r["sample"])]
                for r in skill_rows
            ],
            col_widths=[8 * cm, 3.5 * cm, 3 * cm, 3.5 * cm],
        )
    else:
        pdf.paragraph("Nenhuma habilidade com registro no recorte selecionado.")

    pdf.section(data.get("ranking_title") or "Comparativo")
    ranking = data.get("ranking") or []
    if ranking:
        pdf.table(
            ["Item", "Detalhe", "Indicador", "%"],
            [[r["label"], r.get("detail") or "—", r.get("value") or "—", f"{r.get('pct', 0)}%"] for r in ranking],
            col_widths=[7 * cm, 4 * cm, 4 * cm, 3 * cm],
        )
    else:
        pdf.paragraph("Sem comparativo para o recorte selecionado.")

    a11y = data.get("a11y_stats") or {}
    pdf.section("Acessibilidade (agregado administrativo)")
    pdf.kv_grid(
        [
            ("Sessões com recurso de acesso", str(a11y.get("sessions_with_accessibility", 0))),
            ("Sessões adaptadas", str(a11y.get("sessions_adapted", 0))),
            ("Cobertura de variantes", f"{a11y.get('variant_coverage_pct', 0)}%"),
            ("Bloqueios de acessibilidade", str(a11y.get("accessibility_blocks", 0))),
        ]
    )
    pdf.note(
        "Documento administrativo-pedagógico. Não utiliza comparação entre "
        "estudantes com e sem deficiência e não constitui diagnóstico clínico."
    )
    return pdf.build()


def build_network_pdf(data: dict) -> bytes:
    muni = data.get("municipality")
    pdf = MitakaPdfBuilder(
        title="Relatório da rede municipal",
        subtitle=f"{muni.name}/{muni.state}" if muni else "Rede",
        meta=str(data.get("year") or ""),
    )
    a11y = data.get("a11y_stats") or {}
    pdf.kv_grid(
        [
            ("Escolas", str(data.get("schools_count", 0))),
            ("Estudantes", str(data.get("students_count", 0))),
            ("Cobertura avaliativa", f"{data.get('coverage', 0)}%"),
            ("Sessões com recurso de acesso", str(a11y.get("sessions_with_accessibility", 0))),
            ("Cobertura de variantes", f"{a11y.get('variant_coverage_pct', 0)}%"),
            ("Bloqueios de acessibilidade", str(a11y.get("accessibility_blocks", 0))),
        ]
    )
    pdf.section("Indicadores da rede")
    indicators = data.get("indicators") or []
    if indicators:
        pdf.table(
            ["Habilidade", "Métrica", "Valor", "Amostra"],
            [
                [
                    ind.skill.name if ind.skill_id else "Rede",
                    ind.metric_label,
                    str(ind.metric_value),
                    str(ind.sample_size),
                ]
                for ind in indicators
            ],
            col_widths=[7 * cm, 5 * cm, 3 * cm, 3 * cm],
        )
    else:
        pdf.paragraph("Nenhum indicador de rede disponível.")
    pdf.note(
        "Indicadores agregados da rede. Não utilizar comparações do tipo "
        "“alunos especiais × alunos sem deficiência”."
    )
    return pdf.build()
