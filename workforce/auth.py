from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        request = self.context["request"]
        if not request.empresa:
            raise serializers.ValidationError("Empresa não identificada para autenticação.")
        user = authenticate(
            request=request,
            username=attrs.get("email"),
            password=attrs.get("password"),
        )
        if not user:
            raise serializers.ValidationError("Credenciais inválidas.")
        if user.empresa_id != request.empresa.id:
            raise serializers.ValidationError("Usuário não pertence a esta empresa.")
        if not user.is_ativo(empresa_catalog=request.empresa):
            raise serializers.ValidationError("Usuário inativo.")

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "perfil": user.perfil,
            },
        }


class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer
