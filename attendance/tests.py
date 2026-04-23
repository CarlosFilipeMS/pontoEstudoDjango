from datetime import timedelta

from django.utils import timezone

from attendance.models import (
    AdjustmentStatusChoices,
    AutoGenerationReasonChoices,
    PunchTypeChoices,
    TimeAdjustmentRequest,
    TimeEntry,
)
from attendance.services import AdjustmentService, TimeEntryService
from companies.models import Company
from core.test_support import TenantTestCase
from workforce.models import ProfileChoices, User, WorkSchedule
from workforce.test_support import create_colaborador_com_usuario


class TimeEntryServiceTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Company.objects.create(
            cnpj="99887766000155",
            nome="Empresa Ponto",
            email="rh@ponto.com",
            subdominio="ponto",
        )
        self.bind_tenant()
        self.jornada = WorkSchedule.objects.create(
            empresa_id=self.empresa.id,
            nome="Comercial",
            carga_horaria_semana=44,
            hora_inicio=timezone.datetime(2026, 1, 1, 8, 0).time(),
            hora_fim=timezone.datetime(2026, 1, 1, 18, 0).time(),
            hora_inicio_intervalo=timezone.datetime(2026, 1, 1, 12, 0).time(),
            hora_fim_intervalo=timezone.datetime(2026, 1, 1, 13, 0).time(),
            jornada_personalizada=False,
        )
        self.colaborador = create_colaborador_com_usuario(
            matricula="M100",
            email="ana@ponto.com",
            cpf="12345678901",
            nome="Ana",
            cargo="Analista",
            data_nascimento=timezone.datetime(1992, 5, 20).date(),
            empresa_id=self.empresa.id,
            jornada=self.jornada,
        )
        self.admin = User.objects.get(colaborador=self.colaborador)
        self.admin.perfil = ProfileChoices.ADMIN
        self.admin.save(update_fields=["perfil", "updated_at"])

    def test_tipo_ponto_alterna_automaticamente(self):
        ponto1 = TimeEntryService.registrar_ponto(
            colaborador=self.colaborador,
            data_hora=timezone.now(),
        )
        ponto2 = TimeEntryService.registrar_ponto(
            colaborador=self.colaborador,
            data_hora=timezone.now() + timedelta(minutes=5),
        )
        self.assertEqual(ponto1.tipo_ponto, "ENTRADA")
        self.assertEqual(ponto2.tipo_ponto, "SAIDA")

    def test_aprovacao_solicitacao_desativa_ponto_antigo(self):
        ponto_atual = TimeEntryService.registrar_ponto(
            colaborador=self.colaborador,
            data_hora=timezone.now(),
        )
        solicitacao = TimeAdjustmentRequest.objects.create(
            nova_data_hora=timezone.now() + timedelta(hours=1),
            motivo="Correção",
            ponto=ponto_atual,
            colaborador=self.colaborador,
            solicitado_por=self.admin,
            status=AdjustmentStatusChoices.PENDENTE,
        )

        ajuste = AdjustmentService.aprovar_solicitacao(
            solicitacao=solicitacao,
            aprovador=User.objects.create_user(
                email="mestre@ponto.com",
                empresa_id=self.empresa.id,
                password="Master123!",
                perfil=ProfileChoices.MESTRE,
                colaborador=None,
            ),
        )
        ponto_atual.refresh_from_db()
        self.assertFalse(ponto_atual.ativo)
        self.assertEqual(ajuste.status, AdjustmentStatusChoices.APROVADO)

    def test_rejeicao_solicitacao_muda_status_sem_gerar_ponto(self):
        solicitacao = TimeAdjustmentRequest.objects.create(
            nova_data_hora=timezone.now() + timedelta(hours=1),
            motivo="Correção",
            ponto=None,
            colaborador=self.colaborador,
            solicitado_por=self.admin,
            status=AdjustmentStatusChoices.PENDENTE,
        )
        mestre = User.objects.create_user(
            email="mestre-rejeita@ponto.com",
            empresa_id=self.empresa.id,
            password="Master123!",
            perfil=ProfileChoices.MESTRE,
            colaborador=None,
        )

        rejeitada = AdjustmentService.rejeitar_solicitacao(
            solicitacao=solicitacao,
            aprovador=mestre,
        )

        self.assertEqual(rejeitada.status, AdjustmentStatusChoices.REJEITADO)
        self.assertEqual(rejeitada.aprovado_por_id, mestre.id)
        self.assertEqual(TimeEntry.objects.count(), 0)

    def test_solicitacao_reajuste_usa_soft_delete(self):
        solicitacao = TimeAdjustmentRequest.objects.create(
            nova_data_hora=timezone.now() + timedelta(hours=1),
            motivo="Correção",
            ponto=None,
            colaborador=self.colaborador,
            solicitado_por=self.admin,
            status=AdjustmentStatusChoices.PENDENTE,
        )
        self.assertEqual(TimeAdjustmentRequest.objects.ativos().count(), 1)
        solicitacao.ativo = False
        solicitacao.save(update_fields=["ativo", "updated_at"])
        self.assertEqual(TimeAdjustmentRequest.objects.ativos().count(), 0)

    def test_registro_fecha_automaticamente_entrada_aberta_ha_24h(self):
        agora = timezone.now()
        entrada_antiga = TimeEntry.objects.create(
            colaborador=self.colaborador,
            data_hora=agora - timedelta(hours=25),
            tipo_ponto=PunchTypeChoices.ENTRADA,
            ativo=True,
        )

        novo_ponto = TimeEntryService.registrar_ponto(
            colaborador=self.colaborador,
            data_hora=agora,
        )
        auto_saida = TimeEntry.objects.exclude(id=entrada_antiga.id).exclude(id=novo_ponto.id).get()

        self.assertEqual(auto_saida.tipo_ponto, PunchTypeChoices.SAIDA)
        self.assertTrue(auto_saida.gerado_automaticamente)
        self.assertEqual(auto_saida.motivo_geracao, AutoGenerationReasonChoices.AUTO_FECHAMENTO_24H)
        self.assertEqual(novo_ponto.tipo_ponto, PunchTypeChoices.ENTRADA)

    def test_job_fecha_pontos_abertos_ha_24h(self):
        agora = timezone.now()
        TimeEntry.objects.create(
            colaborador=self.colaborador,
            data_hora=agora - timedelta(hours=26),
            tipo_ponto=PunchTypeChoices.ENTRADA,
            ativo=True,
        )

        fechados = TimeEntryService.auto_fechar_pontos_abertos_empresa(
            empresa_id=self.empresa.id,
            reference_now=agora,
        )

        self.assertEqual(fechados, 1)
        self.assertTrue(
            TimeEntry.objects.filter(
                colaborador=self.colaborador,
                tipo_ponto=PunchTypeChoices.SAIDA,
                gerado_automaticamente=True,
                motivo_geracao=AutoGenerationReasonChoices.AUTO_FECHAMENTO_24H,
            ).exists()
        )
