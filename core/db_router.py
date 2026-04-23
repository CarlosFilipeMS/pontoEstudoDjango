"""
Roteamento database-per-tenant.

- Banco `default`: apenas catálogo (`companies` / tabela empresa).
- Aliases `tenant_*`: dados operacionais (workforce, attendance, auth, etc.).
"""

from django.conf import settings

from core.tenant_context import get_current_tenant_db


class TenantDatabaseRouter:
    catalog_alias = "default"

    def _is_catalog(self, db: str) -> bool:
        return db == self.catalog_alias

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "companies":
            return self.catalog_alias
        alias = get_current_tenant_db()
        if not alias:
            raise RuntimeError(
                "Contexto de banco do tenant ausente. "
                "Use subdomínio/header de empresa ou bind_tenant_db nos testes/comandos."
            )
        return alias

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        db_set = {obj1._state.db, obj2._state.db}
        if None in db_set:
            return True
        if self.catalog_alias in db_set and len(db_set) > 1:
            return False
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "companies":
            return self._is_catalog(db)
        if self._is_catalog(db):
            return False
        return True


def tenant_aliases_from_settings() -> list[str]:
    return [alias for alias in settings.DATABASES if alias != TenantDatabaseRouter.catalog_alias]
