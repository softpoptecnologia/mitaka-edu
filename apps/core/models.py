"""Core models and mixins."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def archive(self):
        self.is_active = False
        self.archived_at = timezone.now()
        self.save(update_fields=["is_active", "archived_at", "updated_at"] if hasattr(self, "updated_at") else ["is_active", "archived_at"])


class AuditLog(TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "create", "Criação"
        UPDATE = "update", "Atualização"
        DELETE = "delete", "Exclusão lógica"
        IMPORT = "import", "Importação"
        PERMISSION = "permission", "Permissão"
        ENROLLMENT = "enrollment", "Matrícula"
        INSTRUMENT = "instrument", "Instrumento"
        LOGIN = "login", "Login"
        ACCESSIBILITY = "accessibility", "Acessibilidade"
        SUPPORT_PLAN = "support_plan", "Plano de apoio"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"
