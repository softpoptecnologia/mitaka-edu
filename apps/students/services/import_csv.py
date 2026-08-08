"""CSV import of students — upsert by external_code, create Enrollment."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from django.db import transaction

from apps.core.services.audit import log_action
from apps.schools.models import Classroom, School, SchoolYear
from apps.students.models import Enrollment, ImportError, ImportJob, Student


def parse_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {value}")


@transaction.atomic
def import_students_csv(*, file_obj, school_year: SchoolYear, created_by) -> ImportJob:
    raw = file_obj.read()
    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig")
    else:
        text = raw
    reader = csv.DictReader(io.StringIO(text))
    required = {"matricula", "nome", "escola", "turma", "ano_letivo"}
    fieldnames = {f.strip().lower() for f in (reader.fieldnames or [])}
    job = ImportJob.objects.create(
        created_by=created_by,
        school_year=school_year,
        file_name=getattr(file_obj, "name", "upload.csv"),
        status=ImportJob.Status.RUNNING,
    )
    if not required.issubset(fieldnames):
        job.status = ImportJob.Status.FAILED
        job.summary = f"Cabeçalhos obrigatórios ausentes. Esperado: {sorted(required)}"
        job.save()
        ImportError.objects.create(job=job, row_number=0, message=job.summary)
        return job

    success = 0
    errors = 0
    total = 0
    for idx, row in enumerate(reader, start=2):
        total += 1
        normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        try:
            year_val = int(normalized.get("ano_letivo") or school_year.year)
            if year_val != school_year.year:
                raise ValueError(f"Ano letivo da linha ({year_val}) difere do selecionado ({school_year.year})")
            school = School.objects.get(code=normalized["escola"], is_active=True)
            classroom = Classroom.objects.get(
                school=school,
                school_year=school_year,
                name=normalized["turma"],
                is_active=True,
            )
            student, _ = Student.objects.update_or_create(
                external_code=normalized["matricula"],
                defaults={
                    "full_name": normalized["nome"],
                    "birth_date": parse_date(normalized.get("data_nascimento", "")),
                    "is_active": True,
                },
            )
            Enrollment.objects.update_or_create(
                student=student,
                school_year=school_year,
                defaults={
                    "classroom": classroom,
                    "status": Enrollment.Status.ACTIVE,
                    "is_active": True,
                },
            )
            success += 1
        except Exception as exc:  # noqa: BLE001 — collect row errors for operator feedback
            errors += 1
            ImportError.objects.create(
                job=job,
                row_number=idx,
                message=str(exc),
                raw_data=normalized,
            )

    job.total_rows = total
    job.success_count = success
    job.error_count = errors
    job.status = ImportJob.Status.DONE if errors == 0 or success > 0 else ImportJob.Status.FAILED
    job.summary = f"{success} sucesso(s), {errors} erro(s) em {total} linha(s)."
    job.save()
    log_action(
        actor=created_by,
        action="import",
        object_type="ImportJob",
        object_id=job.pk,
        message=job.summary,
        payload={"file": job.file_name},
    )
    return job
