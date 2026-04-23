from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from companies.models import Company
from core.tenant_database import (
    ensure_tenant_database_registered,
    resolve_tenant_database_name,
    tenant_alias_for_subdomain,
)


class Command(BaseCommand):
    help = (
        "Registra o alias de conexão do tenant no settings e executa migrate "
        "no banco da empresa (PostgreSQL: crie o database antes)."
    )

    def add_arguments(self, parser):
        parser.add_argument("subdominio", type=str, help="Slug da empresa (ex.: acme)")

    def handle(self, *args, **options):
        sub = options["subdominio"]
        try:
            empresa = Company.objects.get(subdominio=sub)
        except Company.DoesNotExist as exc:
            raise CommandError(f"Empresa com subdomínio {sub!r} não existe no catálogo.") from exc

        alias = tenant_alias_for_subdomain(sub)
        db_name = resolve_tenant_database_name(
            subdomain=sub,
            company_database_name=empresa.database_name,
        )
        ensure_tenant_database_registered(alias, db_name)
        self.stdout.write(self.style.NOTICE(f"Migrando banco {alias!r} ({db_name})..."))
        call_command("migrate", database=alias, interactive=False)
        self.stdout.write(self.style.SUCCESS("Concluído."))
