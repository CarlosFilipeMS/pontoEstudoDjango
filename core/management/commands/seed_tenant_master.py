import hashlib
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from companies.models import Company
from core.tenant_context import bind_tenant_db, reset_tenant_db_token
from core.tenant_database import (
    ensure_tenant_database_registered,
    resolve_tenant_database_name,
    tenant_alias_for_subdomain,
)
from workforce.models import ProfileChoices, User


def _cnpj_seed(subdominio: str) -> str:
    """CNPJ numérico determinístico (14 dígitos) só para desenvolvimento/demo."""
    h = hashlib.sha256(subdominio.encode()).hexdigest()
    digits = "".join(c for c in h if c.isdigit())
    if len(digits) < 14:
        digits = (digits * 3)[:14]
    return digits[:14]


class Command(BaseCommand):
    help = (
        "Seed: cria empresa no catálogo, migra o banco do tenant e cria o usuário MESTRE. "
        "Não use CNPJ/email fictícios em produção sem substituir por dados reais."
    )

    def add_arguments(self, parser):
        parser.add_argument("subdominio", type=str, help="Slug único da empresa (ex.: demo)")
        parser.add_argument("email", type=str, help="E-mail do usuário MESTRE (login JWT)")
        parser.add_argument("password", type=str, help="Senha inicial do MESTRE")
        parser.add_argument("--nome", type=str, default="", help="Razão social / nome da empresa")
        parser.add_argument("--cnpj", type=str, default="", help="14 dígitos; se omitido, gera um valor de seed")
        parser.add_argument(
            "--empresa-email",
            type=str,
            default="",
            help="E-mail de contato da empresa no catálogo; padrão: <subdominio>@seed.local",
        )
        parser.add_argument(
            "--skip-catalog-migrate",
            action="store_true",
            help="Não executa migrate no banco catálogo (default)",
        )
        parser.add_argument(
            "--skip-tenant-migrate",
            action="store_true",
            help="Não executa migrate no banco do tenant (só se já estiver atualizado)",
        )
        parser.add_argument(
            "--reset-mestre-password",
            action="store_true",
            help="Se o MESTRE já existir, redefine a senha para o valor informado (útil após seed repetida).",
        )

    def handle(self, *args: Any, **options: Any):
        sub = options["subdominio"].strip().lower()
        email_mestre = options["email"].strip().lower()
        password = options["password"]
        nome = (options["nome"] or f"Empresa {sub}").strip()
        cnpj = (options["cnpj"] or "").strip() or _cnpj_seed(sub)
        if len(cnpj) != 14 or not cnpj.isdigit():
            raise CommandError("CNPJ deve ter exatamente 14 dígitos numéricos.")
        empresa_email = (options["empresa_email"] or "").strip() or f"{sub}@seed.local"

        if not options["skip_catalog_migrate"]:
            self.stdout.write(self.style.NOTICE("Migrando catálogo (database=default)..."))
            call_command("migrate", database="default", interactive=False)

        with transaction.atomic(using="default"):
            empresa, created = Company.objects.get_or_create(
                subdominio=sub,
                defaults={
                    "cnpj": cnpj,
                    "nome": nome,
                    "email": empresa_email,
                    "endereco": "",
                    "contato": "",
                    "database_name": "",
                    "ativo": True,
                },
            )
            if not created:
                self.stdout.write(
                    self.style.WARNING(
                        f"Empresa com subdomínio {sub!r} já existe (id={empresa.id}). "
                        "Reutilizando registro do catálogo."
                    )
                )

        alias = tenant_alias_for_subdomain(sub)
        db_name = resolve_tenant_database_name(
            subdomain=sub,
            company_database_name=empresa.database_name,
        )
        ensure_tenant_database_registered(alias, db_name)

        if not options["skip_tenant_migrate"]:
            self.stdout.write(self.style.NOTICE(f"Migrando tenant {alias!r} ({db_name})..."))
            call_command("migrate", database=alias, interactive=False)

        token = bind_tenant_db(alias)
        try:
            mestre_qs = User.objects.filter(empresa_id=empresa.id, perfil=ProfileChoices.MESTRE)
            if mestre_qs.exists():
                mestre = mestre_qs.order_by("created_at").first()
                if options["reset_mestre_password"]:
                    mestre.set_password(password)
                    mestre.save(update_fields=["password", "updated_at"])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Senha do MESTRE atualizada ({mestre.email}). "
                            "O e-mail passado no comando não altera o cadastro existente."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "Já existe usuário MESTRE para esta empresa no tenant; não criando outro. "
                            "Use --reset-mestre-password para redefinir a senha com o valor informado."
                        )
                    )
            elif User.objects.filter(email=email_mestre).exists():
                raise CommandError(
                    f"Já existe usuário com e-mail {email_mestre!r} neste tenant. "
                    "Escolha outro e-mail ou remova o usuário existente."
                )
            else:
                User.objects.create_user(
                    email=email_mestre,
                    password=password,
                    empresa_id=empresa.id,
                    perfil=ProfileChoices.MESTRE,
                    colaborador=None,
                    is_staff=True,
                    is_superuser=True,
                )
                self.stdout.write(self.style.SUCCESS(f"MESTRE criado: {email_mestre}"))
        finally:
            reset_tenant_db_token(token)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed concluída. Subdomínio: {sub!r} | Tenant DB: {db_name} | "
                f"Login API: header X-Company-Subdomain: {sub}"
            )
        )
