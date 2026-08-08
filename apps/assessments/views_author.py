"""Instrument authoring for técnico / secretaria."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.assessments.forms import InstrumentForm, InstrumentItemForm
from apps.assessments.models import AssessmentInstrument, AssessmentItem, AssessmentOption, ScoringRule, SkillResultMapping
from apps.core.permissions import NetworkRequiredMixin, cadastro_flags, can_write_network
from apps.core.services.cadastro import archive_object, audit, restore_object
from apps.interventions.models import InterventionTemplate


def _forbidden(request):
    return render(request, "admin_panel/forbidden.html", status=403)


def ensure_default_scoring(instrument: AssessmentInstrument) -> None:
    if instrument.scoring_rules.exists():
        return
    items = list(instrument.items.prefetch_related("options"))
    if not items:
        return
    max_score = 0
    for item in items:
        scores = [opt.score_value for opt in item.options.all()]
        max_score += max(scores) if scores else 0
    if max_score <= 0:
        return
    bands = [
        (0, max(0, int(max_score * 0.4)), "needs_support", "Necessita maior mediação", True),
        (max(0, int(max_score * 0.4)) + 1, max(int(max_score * 0.8), 1), "developing", "Em desenvolvimento", False),
        (max(int(max_score * 0.8) + 1, 1), max_score, "demonstrated", "Habilidade demonstrada", False),
    ]
    template = InterventionTemplate.objects.filter(skill=instrument.skill, is_active=True).first()
    for low, high, code, label, attention in bands:
        if high < low:
            continue
        rule = ScoringRule.objects.create(
            instrument=instrument,
            skill=instrument.skill,
            min_score=low,
            max_score=high,
            result_code=code,
            status_code=code,
            label=label,
        )
        SkillResultMapping.objects.create(
            scoring_rule=rule,
            intervention_template=template if attention or code == "developing" else None,
            needs_attention=attention,
        )


class InstrumentCreateView(NetworkRequiredMixin, View):
    def get(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        return render(request, "admin_panel/form.html", {"form": InstrumentForm(), "page_title": "Novo instrumento", "cancel_url": "management:instruments"})

    def post(self, request):
        if not can_write_network(request.user):
            return _forbidden(request)
        form = InstrumentForm(request.POST)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": "Novo instrumento", "cancel_url": "management:instruments"})
        instrument = form.save()
        audit(request, "instrument", instrument, f"Instrumento criado: {instrument.title}")
        messages.success(request, "Instrumento cadastrado. Inclua itens antes de aplicar.")
        return redirect("management:instrument_items", pk=instrument.pk)


class InstrumentUpdateView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        return render(request, "admin_panel/form.html", {"form": InstrumentForm(instance=instrument), "page_title": f"Editar instrumento — {instrument.title}", "cancel_url": "management:instruments"})

    def post(self, request, pk):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        form = InstrumentForm(request.POST, instance=instrument)
        if not form.is_valid():
            return render(request, "admin_panel/form.html", {"form": form, "page_title": f"Editar instrumento — {instrument.title}", "cancel_url": "management:instruments"})
        instrument = form.save()
        if instrument.is_published:
            ensure_default_scoring(instrument)
        audit(request, "instrument", instrument, f"Instrumento atualizado: {instrument.title}")
        messages.success(request, "Instrumento atualizado.")
        return redirect("management:instruments")


class InstrumentArchiveView(NetworkRequiredMixin, View):
    def post(self, request, pk):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        if instrument.is_active:
            return archive_object(request, instrument, redirect_to="management:instruments")
        return restore_object(request, instrument, redirect_to="management:instruments")


class InstrumentItemsView(NetworkRequiredMixin, View):
    def get(self, request, pk):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        return render(
            request,
            "admin_panel/instrument_items.html",
            {
                "instrument": instrument,
                "items": instrument.items.prefetch_related("options"),
                "form": InstrumentItemForm(),
                **cadastro_flags(request.user),
            },
        )

    def post(self, request, pk):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        form = InstrumentItemForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "admin_panel/instrument_items.html",
                {
                    "instrument": instrument,
                    "items": instrument.items.prefetch_related("options"),
                    "form": form,
                    **cadastro_flags(request.user),
                },
            )
        options = form.parsed_options()
        if not options:
            messages.error(request, "Informe ao menos uma alternativa.")
            return redirect("management:instrument_items", pk=instrument.pk)
        order = (instrument.items.order_by("-order").values_list("order", flat=True).first() or 0) + 1
        item = AssessmentItem.objects.create(
            instrument=instrument,
            order=order,
            item_type=form.cleaned_data["item_type"],
            prompt=form.cleaned_data["prompt"],
        )
        for opt in options:
            AssessmentOption.objects.create(item=item, **opt)
        ensure_default_scoring(instrument)
        audit(request, "instrument", item, f"Item adicionado a {instrument.title}")
        messages.success(request, "Item adicionado.")
        return redirect("management:instrument_items", pk=instrument.pk)


class InstrumentItemDeleteView(NetworkRequiredMixin, View):
    def post(self, request, pk, item_id):
        instrument = get_object_or_404(AssessmentInstrument, pk=pk)
        item = get_object_or_404(AssessmentItem, pk=item_id, instrument=instrument)
        item.delete()
        instrument.scoring_rules.all().delete()
        ensure_default_scoring(instrument)
        messages.success(request, "Item removido.")
        return redirect("management:instrument_items", pk=instrument.pk)
