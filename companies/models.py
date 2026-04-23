from django.db import models
import uuid
from core.models import ActiveModel, TimeStampedModel


class CompanyQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)


class CompanyManager(models.Manager):
    def get_queryset(self):
        return CompanyQuerySet(self.model, using="default")

    def ativos(self):
        return self.get_queryset().ativos()


class Company(TimeStampedModel, ActiveModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cnpj = models.CharField(max_length=14, unique=True)
    nome = models.CharField(max_length=255)
    endereco = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    contato = models.CharField(max_length=30, blank=True)
    subdominio = models.SlugField(max_length=50, unique=True)
    timezone = models.CharField(
        max_length=64,
        default="America/Sao_Paulo",
        help_text="Timezone IANA da empresa para regras temporais de dominio.",
    )
    database_name = models.CharField(
        max_length=128,
        blank=True,
        help_text="PostgreSQL: nome do banco do tenant. Vazio em dev: SQLite em TENANTS_DIR/<subdominio>.sqlite3",
    )

    objects = CompanyManager()

    def save(self, *args, **kwargs):
        kwargs["using"] = "default"
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs["using"] = "default"
        return super().delete(*args, **kwargs)

    class Meta:
        db_table = "empresa"
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return f"{self.nome} ({self.subdominio})"
