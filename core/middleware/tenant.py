from django.http import JsonResponse

from companies.models import Company
from core.tenant_context import bind_tenant_db, reset_tenant_db_token
from core.tenant_database import (
    ensure_tenant_database_registered,
    resolve_tenant_database_name,
    tenant_alias_for_subdomain,
)


class TenantMiddleware:
    """
    Resolve empresa no banco catálogo (default) e associa o alias de banco do tenant
    ao request (contextvar + request.tenant_db).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        host_parts = host.split(".")
        subdomain = request.headers.get("X-Company-Subdomain")

        if not subdomain and len(host_parts) > 2:
            subdomain = host_parts[0]

        request.empresa = None
        request.company = None
        request.tenant_db = None
        token = None

        if subdomain:
            try:
                empresa = Company.objects.ativos().get(subdominio=subdomain)
            except Company.DoesNotExist:
                return JsonResponse(
                    {"detail": "Empresa não encontrada para o subdomínio informado."},
                    status=400,
                )
            alias = tenant_alias_for_subdomain(subdomain)
            db_name = resolve_tenant_database_name(
                subdomain=subdomain,
                company_database_name=empresa.database_name,
            )
            ensure_tenant_database_registered(alias, db_name)
            token = bind_tenant_db(alias)
            request.empresa = empresa
            request.company = empresa
            request.tenant_db = alias

        try:
            return self.get_response(request)
        finally:
            if token is not None:
                reset_tenant_db_token(token)
