"""Helpers para testes que criam colaborador + usuário vinculado."""

from workforce.models import Collaborator, ProfileChoices, User


def create_colaborador_com_usuario(*, empresa_id, jornada, password: str = "TesteSenha123!", **colab_fields) -> Collaborator:
    colaborador = Collaborator.objects.create(empresa_id=empresa_id, jornada=jornada, **colab_fields)
    User.objects.create_user(
        email=colaborador.email,
        empresa_id=colaborador.empresa_id,
        password=password,
        perfil=ProfileChoices.COLABORADOR,
        colaborador=colaborador,
    )
    return colaborador
