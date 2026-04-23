from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings


def tenant_alias_for_subdomain(subdomain: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", subdomain.lower())
    return f"tenant_{safe}"


def resolve_tenant_database_name(*, subdomain: str, company_database_name: str) -> str:
    """
    Nome físico do banco (PostgreSQL) ou caminho absoluto (SQLite em dev).
    Se `company_database_name` vazio, usa arquivo em TENANTS_DIR.
    """
    if company_database_name:
        return company_database_name
    tenants_dir: Path = settings.TENANTS_DIR
    tenants_dir.mkdir(parents=True, exist_ok=True)
    return str(tenants_dir / f"{subdomain}.sqlite3")


def ensure_tenant_database_registered(alias: str, database_name: str) -> None:
    """Registra alias em DATABASES antes do primeiro uso da conexão."""
    if alias in settings.DATABASES:
        existing = settings.DATABASES[alias]
        if existing.get("NAME") != database_name:
            raise RuntimeError(
                f"Alias de banco {alias!r} já registrado com NAME diferente. "
                "Conflito de configuração de tenant."
            )
        return
    # Copiar defaults já normalizados pelo Django (TIME_ZONE, TEST, etc.)
    cfg = dict(settings.DATABASES["default"])
    cfg.update(settings.TENANT_DATABASE_BASE)
    cfg["NAME"] = database_name
    settings.DATABASES[alias] = cfg
