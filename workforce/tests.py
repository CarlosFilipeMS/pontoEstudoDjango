from datetime import date, time

from rest_framework.exceptions import PermissionDenied, ValidationError

from companies.models import Company
from core.test_support import TenantTestCase
from workforce.models import Collaborator, ProfileChoices, User, WorkSchedule
from workforce.services import AdminManagementService
from workforce.test_support import create_colaborador_com_usuario


class UserAtivacaoGlobalTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Company.objects.create(
            cnpj="12345678000199",
            nome="Empresa Teste",
            email="contato@empresa.com",
            subdominio="empresa",
        )
        self.bind_tenant()
        self.jornada = WorkSchedule.objects.create(
            empresa_id=self.empresa.id,
            nome="Padrao",
            carga_horaria_semana=40,
            hora_inicio=time(8, 0),
            hora_fim=time(17, 0),
            hora_inicio_intervalo=time(12, 0),
            hora_fim_intervalo=time(13, 0),
            jornada_personalizada=False,
        )
        self.colaborador = create_colaborador_com_usuario(
            matricula="M001",
            email="colaborador@empresa.com",
            cpf="11122233344",
            nome="Colaborador 1",
            cargo="Dev",
            data_nascimento=date(1990, 1, 1),
            empresa_id=self.empresa.id,
            jornada=self.jornada,
        )
        self.usuario = User.objects.get(colaborador=self.colaborador)

    def test_usuario_ativo_global_true(self):
        self.assertTrue(self.usuario.is_ativo(empresa_catalog=self.empresa))

    def test_usuario_inativo_quando_empresa_inativa(self):
        self.empresa.ativo = False
        self.empresa.save()
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_ativo(empresa_catalog=self.empresa))

    def test_perfil_mestre_sem_colaborador(self):
        mestre = User.objects.create_user(
            email="mestre@empresa.com",
            empresa_id=self.empresa.id,
            password="Teste123!",
            perfil=ProfileChoices.MESTRE,
            colaborador=None,
        )
        self.assertIsNone(mestre.colaborador)


class AdminManagementServiceTestCase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Company.objects.create(
            cnpj="22334455000166",
            nome="Empresa Gestao",
            email="contato@gestao.com",
            subdominio="gestao",
        )
        self.bind_tenant()
        self.jornada = WorkSchedule.objects.create(
            empresa_id=self.empresa.id,
            nome="Padrao",
            carga_horaria_semana=40,
            hora_inicio=time(8, 0),
            hora_fim=time(17, 0),
            hora_inicio_intervalo=time(12, 0),
            hora_fim_intervalo=time(13, 0),
            jornada_personalizada=False,
        )
        self.colaborador_1 = create_colaborador_com_usuario(
            matricula="M200",
            email="colab1@gestao.com",
            cpf="99988877766",
            nome="Colab 1",
            cargo="Analista",
            data_nascimento=date(1993, 6, 1),
            empresa_id=self.empresa.id,
            jornada=self.jornada,
        )
        self.colaborador_2 = create_colaborador_com_usuario(
            matricula="M201",
            email="colab2@gestao.com",
            cpf="88877766655",
            nome="Colab 2",
            cargo="Analista",
            data_nascimento=date(1994, 6, 1),
            empresa_id=self.empresa.id,
            jornada=self.jornada,
        )
        self.usuario_admin = User.objects.get(colaborador=self.colaborador_1)
        self.usuario_admin.perfil = ProfileChoices.ADMIN
        self.usuario_admin.save(update_fields=["perfil", "updated_at"])
        self.usuario_colaborador = User.objects.get(colaborador=self.colaborador_2)
        self.mestre = User.objects.create_user(
            email="mestre@gestao.com",
            empresa_id=self.empresa.id,
            password="Master123!",
            perfil=ProfileChoices.MESTRE,
            colaborador=None,
        )

    def test_admin_promove_colaborador_para_admin(self):
        alvo = AdminManagementService.promover_para_admin(
            solicitante=self.usuario_admin,
            alvo=self.usuario_colaborador,
        )
        self.assertEqual(alvo.perfil, ProfileChoices.ADMIN)

    def test_admin_nao_rebaixa_admin(self):
        self.usuario_colaborador.perfil = ProfileChoices.ADMIN
        self.usuario_colaborador.save(update_fields=["perfil", "updated_at"])
        with self.assertRaises(PermissionDenied):
            AdminManagementService.rebaixar_admin(
                solicitante=self.usuario_admin,
                alvo=self.usuario_colaborador,
            )

    def test_mestre_rebaixa_admin(self):
        alvo = AdminManagementService.rebaixar_admin(
            solicitante=self.mestre,
            alvo=self.usuario_admin,
        )
        self.assertEqual(alvo.perfil, ProfileChoices.COLABORADOR)

    def test_usuario_nao_altera_proprio_perfil(self):
        with self.assertRaises(ValidationError):
            AdminManagementService.promover_para_admin(
                solicitante=self.usuario_colaborador,
                alvo=self.usuario_colaborador,
            )
