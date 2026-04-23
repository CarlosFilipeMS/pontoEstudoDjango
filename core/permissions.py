from rest_framework.permissions import BasePermission


class IsUsuarioAtivoGlobal(BasePermission):
    message = "Usuário inativo para esta empresa."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        empresa = getattr(request, "empresa", None)
        if empresa is not None and empresa.id == user.empresa_id:
            return user.is_ativo(empresa_catalog=empresa)
        return user.is_ativo()


class IsMestre(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.perfil == "MESTRE"


class IsAdminOuMestre(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.perfil in {"ADMIN", "MESTRE"}


class IsColaborador(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.perfil == "COLABORADOR"
