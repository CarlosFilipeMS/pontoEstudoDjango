import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from companies.models import Company
from core.models import ActiveModel, TimeStampedModel


class ProfileChoices(models.TextChoices):
    MESTRE = "MESTRE", "Mestre"
    ADMIN = "ADMIN", "Admin"
    COLABORADOR = "COLABORADOR", "Colaborador"


class UserQuerySet(models.QuerySet):
    def da_empresa(self, empresa):
        eid = empresa.id if hasattr(empresa, "id") else empresa
        return self.filter(empresa_id=eid)

    def ativos(self):
        return self.filter(ativo=True).filter(
            Q(colaborador__isnull=True) | Q(colaborador__ativo=True),
        )


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def da_empresa(self, empresa):
        return self.get_queryset().da_empresa(empresa)

    def ativos(self):
        return self.get_queryset().ativos()

    def create_user(self, email, password=None, empresa=None, empresa_id=None, **extra_fields):
        if not email:
            raise ValueError("Email é obrigatório")
        if empresa is not None:
            empresa_id = empresa.id
        if empresa_id is None:
            raise ValueError("Empresa é obrigatória")
        email = self.normalize_email(email)
        user = self.model(email=email, empresa_id=empresa_id, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        empresa = extra_fields.pop("empresa", None)
        empresa_id = extra_fields.pop("empresa_id", None)
        if empresa is not None:
            empresa_id = empresa.id
        if empresa_id is None:
            raise ValueError("Superuser precisa de empresa_id ou empresa.")
        extra_fields.setdefault("perfil", ProfileChoices.MESTRE)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, empresa_id=empresa_id, **extra_fields)


class WorkScheduleQuerySet(models.QuerySet):
    def da_empresa(self, empresa):
        eid = empresa.id if hasattr(empresa, "id") else empresa
        return self.filter(empresa_id=eid)

    def ativos(self):
        return self.filter(ativo=True)


class WorkSchedule(TimeStampedModel, ActiveModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa_id = models.UUIDField(db_index=True)
    nome = models.CharField(max_length=120)
    carga_horaria_semana = models.PositiveIntegerField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    hora_inicio_intervalo = models.TimeField()
    hora_fim_intervalo = models.TimeField()
    jornada_personalizada = models.BooleanField(default=False)

    objects = WorkScheduleQuerySet.as_manager()

    class Meta:
        db_table = "jornada"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "nome"],
                name="uniq_jornada_nome_por_empresa",
            ),
            models.CheckConstraint(
                condition=Q(carga_horaria_semana__gt=0),
                name="ck_jornada_carga_maior_que_zero",
            ),
        ]

    def __str__(self):
        return f"{self.nome} ({self.empresa_id})"


class CollaboratorQuerySet(models.QuerySet):
    def da_empresa(self, empresa):
        eid = empresa.id if hasattr(empresa, "id") else empresa
        return self.filter(empresa_id=eid)

    def ativos(self):
        return self.filter(ativo=True)


class Collaborator(TimeStampedModel, ActiveModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matricula = models.CharField(max_length=40)
    email = models.EmailField()
    cpf = models.CharField(max_length=14)
    nome = models.CharField(max_length=255)
    cargo = models.CharField(max_length=120)
    data_nascimento = models.DateField()
    empresa_id = models.UUIDField(db_index=True)
    jornada = models.ForeignKey(
        WorkSchedule,
        on_delete=models.PROTECT,
        related_name="colaboradores",
    )

    objects = CollaboratorQuerySet.as_manager()

    class Meta:
        db_table = "colaborador"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "matricula"],
                name="uniq_colaborador_matricula_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["empresa_id", "email"],
                name="uniq_colaborador_email_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["empresa_id", "cpf"],
                name="uniq_colaborador_cpf_por_empresa",
            ),
        ]

    def clean(self):
        if self.jornada and self.empresa_id != self.jornada.empresa_id:
            raise ValidationError("Jornada deve pertencer à mesma empresa do colaborador.")

    def __str__(self):
        return self.nome


class User(TimeStampedModel, ActiveModel, AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    perfil = models.CharField(max_length=20, choices=ProfileChoices.choices)
    empresa_id = models.UUIDField(db_index=True)
    colaborador = models.OneToOneField(
        Collaborator,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuario",
    )
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["empresa_id"]

    class Meta:
        db_table = "usuario"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id"],
                condition=Q(perfil=ProfileChoices.MESTRE),
                name="uniq_usuario_mestre_por_empresa",
            ),
            models.CheckConstraint(
                condition=Q(perfil=ProfileChoices.MESTRE, colaborador__isnull=True)
                | Q(
                    perfil__in=[
                        ProfileChoices.ADMIN,
                        ProfileChoices.COLABORADOR,
                    ],
                    colaborador__isnull=False,
                ),
                name="ck_usuario_perfil_colaborador",
            ),
        ]

    def clean(self):
        if self.colaborador and self.colaborador.empresa_id != self.empresa_id:
            raise ValidationError("Usuário não pode ser vinculado a colaborador de outra empresa.")

    def is_ativo(self, empresa_catalog: Company | None = None):
        colaborador_ativo = self.colaborador is None or self.colaborador.ativo
        if not self.ativo or not colaborador_ativo:
            return False
        if empresa_catalog is not None and empresa_catalog.id == self.empresa_id:
            return empresa_catalog.ativo
        try:
            emp = Company.objects.get(pk=self.empresa_id)
        except Company.DoesNotExist:
            return False
        return emp.ativo

    def __str__(self):
        return self.email
