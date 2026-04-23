from datetime import timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from attendance.models import (
    AutoGenerationReasonChoices,
    AdjustmentStatusChoices,
    PunchTypeChoices,
    TimeAdjustmentRequest,
    TimeEntry,
)
from companies.models import Company
from workforce.models import Collaborator


class TimeEntryService:
    @staticmethod
    def _resolve_company_timezone(empresa_id):
        empresa = Company.objects.get(pk=empresa_id)
        return ZoneInfo(empresa.timezone)

    @classmethod
    def _auto_close_open_entry_if_needed(cls, *, colaborador, reference_now, lock_row):
        query = TimeEntry.objects.filter(colaborador=colaborador, ativo=True).order_by("-data_hora")
        if lock_row:
            query = query.select_for_update()
        ultimo = query.first()
        if ultimo is None or ultimo.tipo_ponto != PunchTypeChoices.ENTRADA:
            return ultimo, None

        tz_empresa = cls._resolve_company_timezone(colaborador.empresa_id)
        now_local = reference_now.astimezone(tz_empresa)
        entrada_local = ultimo.data_hora.astimezone(tz_empresa)
        auto_close_minutes = settings.AUTO_CLOSE_OPEN_ENTRY_MINUTES
        fechamento_local = entrada_local + timedelta(minutes=auto_close_minutes)
        if now_local < fechamento_local:
            return ultimo, None

        fechamento = fechamento_local.astimezone(dt_timezone.utc)
        auto_saida = TimeEntry.objects.create(
            colaborador=colaborador,
            data_hora=fechamento,
            tipo_ponto=PunchTypeChoices.SAIDA,
            ativo=True,
            gerado_automaticamente=True,
            motivo_geracao=AutoGenerationReasonChoices.AUTO_FECHAMENTO_24H,
        )
        return auto_saida, auto_saida

    @classmethod
    @transaction.atomic
    def auto_fechar_pontos_abertos_empresa(cls, *, empresa_id, reference_now=None):
        if reference_now is None:
            reference_now = timezone.now()
        fechados = 0
        colaboradores = Collaborator.objects.filter(empresa_id=empresa_id, ativo=True).only("id", "empresa_id")
        for colaborador in colaboradores:
            _, auto_saida = cls._auto_close_open_entry_if_needed(
                colaborador=colaborador,
                reference_now=reference_now,
                lock_row=True,
            )
            if auto_saida:
                fechados += 1
        return fechados

    @staticmethod
    @transaction.atomic
    def registrar_ponto(*, colaborador, data_hora):
        reference_now = timezone.now()
        ultimo, _ = TimeEntryService._auto_close_open_entry_if_needed(
            colaborador=colaborador,
            reference_now=reference_now,
            lock_row=True,
        )
        if ultimo is None or ultimo.tipo_ponto == PunchTypeChoices.SAIDA:
            tipo = PunchTypeChoices.ENTRADA
        else:
            tipo = PunchTypeChoices.SAIDA

        return TimeEntry.objects.create(
            colaborador=colaborador,
            data_hora=data_hora,
            tipo_ponto=tipo,
            ativo=True,
        )


class AdjustmentService:
    @staticmethod
    def _assert_pode_processar_solicitacao(*, solicitacao: TimeAdjustmentRequest, aprovador):
        if solicitacao.status != AdjustmentStatusChoices.PENDENTE:
            raise ValidationError("Somente solicitação pendente pode ser processada.")

        if aprovador.perfil == "ADMIN" and solicitacao.solicitado_por_id == aprovador.id:
            raise PermissionDenied("ADMIN não pode processar a própria solicitação de ajuste.")

        if aprovador.perfil == "COLABORADOR":
            raise PermissionDenied("Colaborador não pode processar solicitação.")

    @staticmethod
    @transaction.atomic
    def aprovar_solicitacao(*, solicitacao: TimeAdjustmentRequest, aprovador):
        solicitacao = TimeAdjustmentRequest.objects.select_for_update().get(pk=solicitacao.pk)
        AdjustmentService._assert_pode_processar_solicitacao(solicitacao=solicitacao, aprovador=aprovador)

        ponto_original_raiz = solicitacao.ponto.ponto_original if solicitacao.ponto else None
        if solicitacao.ponto and solicitacao.ponto.ativo:
            solicitacao.ponto.ativo = False
            solicitacao.ponto.save(update_fields=["ativo", "updated_at"])

        novo_ponto = TimeEntryService.registrar_ponto(
            colaborador=solicitacao.colaborador,
            data_hora=solicitacao.nova_data_hora,
        )
        if solicitacao.ponto:
            novo_ponto.ponto_original = ponto_original_raiz or solicitacao.ponto
            novo_ponto.save(update_fields=["ponto_original", "updated_at"])

        raiz = novo_ponto.ponto_original or novo_ponto
        ativos_na_cadeia = TimeEntry.objects.filter(
            Q(id=raiz.id) | Q(ponto_original=raiz),
            ativo=True,
        )
        if ativos_na_cadeia.count() > 1:
            raise ValidationError("A cadeia de ajustes deve possuir somente um ponto ativo.")

        solicitacao.status = AdjustmentStatusChoices.APROVADO
        solicitacao.aprovado_por = aprovador
        solicitacao.ponto_resultante = novo_ponto
        solicitacao.save(update_fields=["status", "aprovado_por", "ponto_resultante", "updated_at"])
        return solicitacao

    @staticmethod
    @transaction.atomic
    def rejeitar_solicitacao(*, solicitacao: TimeAdjustmentRequest, aprovador):
        solicitacao = TimeAdjustmentRequest.objects.select_for_update().get(pk=solicitacao.pk)
        AdjustmentService._assert_pode_processar_solicitacao(solicitacao=solicitacao, aprovador=aprovador)
        solicitacao.status = AdjustmentStatusChoices.REJEITADO
        solicitacao.aprovado_por = aprovador
        solicitacao.save(update_fields=["status", "aprovado_por", "updated_at"])
        return solicitacao
