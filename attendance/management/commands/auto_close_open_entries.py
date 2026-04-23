from django.core.management.base import BaseCommand, CommandError

from attendance.services import TimeEntryService
from companies.models import Company
from core.tenant_context import bind_tenant_db, reset_tenant_db_token
from core.tenant_database import (
    ensure_tenant_database_registered,
    resolve_tenant_database_name,
    tenant_alias_for_subdomain,
)


class Command(BaseCommand):
    help = (
        "Fecha automaticamente pontos abertos ha mais de 24h "
        "criando SAIDA automatica (timezone da empresa)."
    )

    def add_arguments(self, parser):
        parser.add_argument("subdominio", type=str, help="Subdominio da empresa alvo.")

    def handle(self, *args, **options):
        subdominio = options["subdominio"]
        try:
            empresa = Company.objects.ativos().get(subdominio=subdominio)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Empresa ativa com subdominio {subdominio!r} nao encontrada.") from exc

        alias = tenant_alias_for_subdomain(subdominio)
        db_name = resolve_tenant_database_name(
            subdomain=subdominio,
            company_database_name=empresa.database_name,
        )
        ensure_tenant_database_registered(alias, db_name)

        token = bind_tenant_db(alias)
        try:
            fechados = TimeEntryService.auto_fechar_pontos_abertos_empresa(empresa_id=empresa.id)
        finally:
            reset_tenant_db_token(token)

        self.stdout.write(
            self.style.SUCCESS(
                f"Auto fechamento concluido para {subdominio!r}. Pontos fechados: {fechados}."
            )
        )
