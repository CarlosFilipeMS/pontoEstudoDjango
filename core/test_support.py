"""Utilitários de teste para multi-database."""

from contextvars import Token

from django.test import TestCase

from core.tenant_context import bind_tenant_db, reset_tenant_db_token


class TenantTestCase(TestCase):
    """Catálogo em `default`; dados operacionais em `tenant_test`."""

    databases = {"default", "tenant_test"}
    _tenant_token: Token | None = None

    def bind_tenant(self, alias: str = "tenant_test") -> None:
        if self._tenant_token is not None:
            reset_tenant_db_token(self._tenant_token)
        self._tenant_token = bind_tenant_db(alias)

    def tearDown(self):
        if self._tenant_token is not None:
            reset_tenant_db_token(self._tenant_token)
            self._tenant_token = None
        super().tearDown()
