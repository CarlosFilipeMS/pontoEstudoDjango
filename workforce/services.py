from rest_framework.exceptions import PermissionDenied, ValidationError

from workforce.models import ProfileChoices, User


class AdminManagementService:
    @staticmethod
    def promover_para_admin(*, solicitante: User, alvo: User):
        if solicitante.id == alvo.id:
            raise ValidationError("Usuário não pode alterar o próprio perfil.")
        if alvo.perfil != ProfileChoices.COLABORADOR:
            raise ValidationError("Apenas COLABORADOR pode ser promovido para ADMIN.")
        if solicitante.perfil not in {ProfileChoices.ADMIN, ProfileChoices.MESTRE}:
            raise PermissionDenied("Somente ADMIN ou MESTRE pode promover administrador.")
        alvo.perfil = ProfileChoices.ADMIN
        alvo.save(update_fields=["perfil", "updated_at"])
        return alvo

    @staticmethod
    def rebaixar_admin(*, solicitante: User, alvo: User):
        if solicitante.id == alvo.id:
            raise ValidationError("Usuário não pode alterar o próprio perfil.")
        if solicitante.perfil != ProfileChoices.MESTRE:
            raise PermissionDenied("Somente o perfil MESTRE pode rebaixar ADMIN.")
        if alvo.perfil != ProfileChoices.ADMIN:
            raise ValidationError("Este perfil não pode ser rebaixado.")
        alvo.perfil = ProfileChoices.COLABORADOR
        alvo.save(update_fields=["perfil", "updated_at"])
        return alvo
