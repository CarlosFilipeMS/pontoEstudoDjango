from django.db import models
import uuid

from django.db.models import Q

from core.models import ActiveModel, TimeStampedModel
from workforce.models import Collaborator, User


class PunchTypeChoices(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SAIDA = "SAIDA", "Saida"


class AutoGenerationReasonChoices(models.TextChoices):
    NONE = "", "Nenhum"
    AUTO_FECHAMENTO_24H = "AUTO_FECHAMENTO_24H", "Auto fechamento 24h"


class TimeEntryQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)

    def da_empresa(self, empresa):
        eid = empresa.id if hasattr(empresa, "id") else empresa
        return self.filter(colaborador__empresa_id=eid)


class TimeEntry(TimeStampedModel, ActiveModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_hora = models.DateTimeField()
    tipo_ponto = models.CharField(max_length=10, choices=PunchTypeChoices.choices)
    colaborador = models.ForeignKey(Collaborator, on_delete=models.PROTECT, related_name="pontos")
    ponto_original = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ajustes",
    )
    gerado_automaticamente = models.BooleanField(default=False, db_index=True)
    motivo_geracao = models.CharField(
        max_length=40,
        choices=AutoGenerationReasonChoices.choices,
        blank=True,
        default=AutoGenerationReasonChoices.NONE,
    )

    objects = TimeEntryQuerySet.as_manager()

    class Meta:
        db_table = "ponto"
        constraints = [
            models.UniqueConstraint(
                fields=["colaborador", "data_hora", "ativo"],
                name="uniq_ponto_colaborador_data_hora_ativo",
            ),
            models.CheckConstraint(
                condition=Q(tipo_ponto=PunchTypeChoices.ENTRADA) | Q(tipo_ponto=PunchTypeChoices.SAIDA),
                name="ck_ponto_tipo_valido",
            ),
            models.CheckConstraint(
                condition=Q(gerado_automaticamente=False, motivo_geracao="")
                | Q(gerado_automaticamente=True, motivo_geracao__gt=""),
                name="ck_ponto_geracao_automatica_consistente",
            ),
        ]
        indexes = [
            models.Index(fields=["colaborador", "-data_hora"]),
        ]


class AdjustmentStatusChoices(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    APROVADO = "APROVADO", "Aprovado"
    REJEITADO = "REJEITADO", "Rejeitado"


class TimeAdjustmentRequestQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)

    def da_empresa(self, empresa):
        eid = empresa.id if hasattr(empresa, "id") else empresa
        return self.filter(colaborador__empresa_id=eid)


class TimeAdjustmentRequest(TimeStampedModel, ActiveModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nova_data_hora = models.DateTimeField()
    status = models.CharField(
        max_length=15,
        choices=AdjustmentStatusChoices.choices,
        default=AdjustmentStatusChoices.PENDENTE,
    )
    motivo = models.TextField()
    ponto = models.ForeignKey(
        TimeEntry,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitacoes",
    )
    ponto_resultante = models.ForeignKey(
        TimeEntry,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitacoes_resultantes",
    )
    colaborador = models.ForeignKey(
        Collaborator,
        on_delete=models.PROTECT,
        related_name="solicitacoes_ajuste",
    )
    aprovado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ajustes_aprovados",
    )
    solicitado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="ajustes_solicitados",
    )

    objects = TimeAdjustmentRequestQuerySet.as_manager()

    class Meta:
        db_table = "solicitacao_reajuste"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[choice for choice, _ in AdjustmentStatusChoices.choices]),
                name="ck_solicitacao_status_valido",
            ),
        ]
