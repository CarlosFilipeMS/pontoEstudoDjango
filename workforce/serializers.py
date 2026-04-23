from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from workforce.models import Collaborator, ProfileChoices, User, WorkSchedule


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = (
            "id",
            "nome",
            "carga_horaria_semana",
            "hora_inicio",
            "hora_fim",
            "hora_inicio_intervalo",
            "hora_fim_intervalo",
            "jornada_personalizada",
            "ativo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context["request"]
        if not request.empresa:
            raise serializers.ValidationError("Empresa não identificada no request.")
        return attrs


class CollaboratorSerializer(serializers.ModelSerializer):
    """Na criação, `senha_inicial` define a senha do `User` gerado (não fica no modelo Colaborador)."""

    senha_inicial = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Collaborator
        fields = (
            "id",
            "matricula",
            "email",
            "cpf",
            "nome",
            "cargo",
            "data_nascimento",
            "jornada",
            "ativo",
            "senha_inicial",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_jornada(self, value):
        request = self.context["request"]
        if value.empresa_id != request.empresa.id:
            raise serializers.ValidationError("Jornada deve ser da mesma empresa.")
        return value

    def validate(self, attrs):
        if self.instance is not None and "senha_inicial" in attrs:
            raise serializers.ValidationError(
                {"senha_inicial": "Senha do usuário não pode ser alterada neste endpoint."}
            )
        if self.instance is None:
            senha = attrs.get("senha_inicial")
            if not senha:
                raise serializers.ValidationError(
                    {"senha_inicial": "Obrigatório ao criar colaborador (senha do usuário vinculado)."}
                )
        return attrs

    def validate_senha_inicial(self, value):
        if value is None:
            return value
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        request = self.context["request"]
        if not request.empresa:
            raise serializers.ValidationError("Empresa não identificada no request.")
        senha = validated_data.pop("senha_inicial")
        with transaction.atomic():
            colaborador = Collaborator.objects.create(empresa_id=request.empresa.id, **validated_data)
            User.objects.create_user(
                email=colaborador.email,
                empresa_id=colaborador.empresa_id,
                password=senha,
                perfil=ProfileChoices.COLABORADOR,
                colaborador=colaborador,
            )
        return colaborador

    def update(self, instance, validated_data):
        validated_data.pop("senha_inicial", None)
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "perfil",
            "empresa_id",
            "colaborador",
            "ativo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "empresa_id", "created_at", "updated_at")
