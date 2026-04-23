from rest_framework import serializers

from attendance.models import AdjustmentStatusChoices, TimeAdjustmentRequest, TimeEntry
from attendance.services import AdjustmentService, TimeEntryService
from workforce.models import Collaborator


class TimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "data_hora",
            "tipo_ponto",
            "colaborador",
            "ponto_original",
            "gerado_automaticamente",
            "motivo_geracao",
            "ativo",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tipo_ponto",
            "ponto_original",
            "gerado_automaticamente",
            "motivo_geracao",
            "ativo",
            "created_at",
            "updated_at",
        )

    def validate_colaborador(self, value):
        request = self.context["request"]
        if value.empresa_id != request.empresa.id:
            raise serializers.ValidationError("Colaborador não pertence à empresa da request.")
        user = request.user
        if user.perfil == "COLABORADOR" and user.colaborador_id != value.id:
            raise serializers.ValidationError("Colaborador só pode registrar o próprio ponto.")
        if user.perfil == "MESTRE":
            raise serializers.ValidationError("Usuário mestre não pode registrar ponto.")
        return value

    def create(self, validated_data):
        return TimeEntryService.registrar_ponto(
            colaborador=validated_data["colaborador"],
            data_hora=validated_data["data_hora"],
        )


class TimeAdjustmentRequestSerializer(serializers.ModelSerializer):
    colaborador_nome = serializers.CharField(source="colaborador.nome", read_only=True)
    solicitado_por_email = serializers.EmailField(source="solicitado_por.email", read_only=True)
    aprovado_por_email = serializers.EmailField(source="aprovado_por.email", read_only=True)

    class Meta:
        model = TimeAdjustmentRequest
        fields = (
            "id",
            "nova_data_hora",
            "status",
            "motivo",
            "ponto",
            "ponto_resultante",
            "colaborador",
            "aprovado_por",
            "solicitado_por",
            "colaborador_nome",
            "solicitado_por_email",
            "aprovado_por_email",
            "ativo",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "ponto_resultante",
            "aprovado_por",
            "solicitado_por",
            "ativo",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        colaborador = attrs["colaborador"]
        if colaborador.empresa_id != request.empresa.id:
            raise serializers.ValidationError("Colaborador fora da empresa.")
        ponto = attrs.get("ponto")
        if ponto and ponto.colaborador_id != colaborador.id:
            raise serializers.ValidationError("Ponto informado não pertence ao colaborador.")
        if request.user.perfil == "COLABORADOR" and request.user.colaborador_id != colaborador.id:
            raise serializers.ValidationError("Colaborador só pode abrir solicitação para si mesmo.")
        return attrs

    def create(self, validated_data):
        validated_data["solicitado_por"] = self.context["request"].user
        return super().create(validated_data)


class AdjustmentApproveSerializer(serializers.Serializer):
    solicitacao_id = serializers.UUIDField()

    def validate_solicitacao_id(self, value):
        request = self.context["request"]
        try:
            solicitacao = TimeAdjustmentRequest.objects.select_related(
                "solicitado_por",
                "colaborador",
                "ponto",
            ).get(id=value, colaborador__empresa_id=request.empresa.id, ativo=True)
        except TimeAdjustmentRequest.DoesNotExist as exc:
            raise serializers.ValidationError("Solicitação não encontrada.") from exc
        if solicitacao.status != AdjustmentStatusChoices.PENDENTE:
            raise serializers.ValidationError("Solicitação não está pendente.")
        self.context["solicitacao"] = solicitacao
        return value

    def save(self, **kwargs):
        return AdjustmentService.aprovar_solicitacao(
            solicitacao=self.context["solicitacao"],
            aprovador=self.context["request"].user,
        )


class AdjustmentRejectSerializer(serializers.Serializer):
    solicitacao_id = serializers.UUIDField()

    def validate_solicitacao_id(self, value):
        request = self.context["request"]
        try:
            solicitacao = TimeAdjustmentRequest.objects.select_related(
                "solicitado_por",
                "colaborador",
                "ponto",
            ).get(id=value, colaborador__empresa_id=request.empresa.id, ativo=True)
        except TimeAdjustmentRequest.DoesNotExist as exc:
            raise serializers.ValidationError("Solicitação não encontrada.") from exc
        if solicitacao.status != AdjustmentStatusChoices.PENDENTE:
            raise serializers.ValidationError("Solicitação não está pendente.")
        self.context["solicitacao"] = solicitacao
        return value

    def save(self, **kwargs):
        return AdjustmentService.rejeitar_solicitacao(
            solicitacao=self.context["solicitacao"],
            aprovador=self.context["request"].user,
        )


class TimeReportQuerySerializer(serializers.Serializer):
    colaborador_id = serializers.UUIDField(required=False)
    inicio = serializers.DateTimeField(required=True)
    fim = serializers.DateTimeField(required=True)

    def validate(self, attrs):
        if attrs["inicio"] > attrs["fim"]:
            raise serializers.ValidationError("Período inválido: inicio deve ser menor ou igual ao fim.")
        return attrs
