from datetime import timedelta

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from attendance.models import PunchTypeChoices, TimeAdjustmentRequest, TimeEntry
from attendance.serializers import (
    AdjustmentApproveSerializer,
    AdjustmentRejectSerializer,
    TimeReportQuerySerializer,
    TimeAdjustmentRequestSerializer,
    TimeEntrySerializer,
)
from core.permissions import IsAdminOuMestre
from workforce.models import Collaborator


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TimeEntry.objects.da_empresa(self.request.empresa).ativos().select_related("colaborador")
        if self.request.user.perfil == "COLABORADOR":
            queryset = queryset.filter(colaborador=self.request.user.colaborador)
        return queryset

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=["ativo", "updated_at"])

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def ultimo(self, request):
        """Último ponto ativo do colaborador vinculado e tipo do próximo registro (regra automática)."""
        if request.user.perfil == "MESTRE":
            return Response({"ultimo": None, "proximo_tipo": None})
        colab = getattr(request.user, "colaborador", None)
        if colab is None:
            return Response({"ultimo": None, "proximo_tipo": None})
        ultimo = (
            TimeEntry.objects.da_empresa(request.empresa)
            .ativos()
            .filter(colaborador=colab)
            .order_by("-data_hora")
            .first()
        )
        if ultimo is None:
            proximo = PunchTypeChoices.ENTRADA
        elif ultimo.tipo_ponto == PunchTypeChoices.ENTRADA:
            proximo = PunchTypeChoices.SAIDA
        else:
            proximo = PunchTypeChoices.ENTRADA
        return Response(
            {
                "ultimo": TimeEntrySerializer(ultimo).data if ultimo else None,
                "proximo_tipo": proximo,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def relatorio(self, request):
        query_serializer = TimeReportQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data
        colaborador_id = data.get("colaborador_id")

        if request.user.perfil == "COLABORADOR":
            if colaborador_id and str(request.user.colaborador_id) != str(colaborador_id):
                return Response(
                    {"detail": "Colaborador só pode consultar o próprio relatório."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            colaborador = request.user.colaborador
        else:
            if not colaborador_id:
                return Response(
                    {"detail": "colaborador_id é obrigatório para ADMIN/MESTRE."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                colaborador = Collaborator.objects.da_empresa(request.empresa).ativos().get(id=colaborador_id)
            except Collaborator.DoesNotExist:
                return Response({"detail": "Colaborador não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        pontos = list(
            TimeEntry.objects.da_empresa(request.empresa)
            .ativos()
            .filter(
                colaborador=colaborador,
                data_hora__gte=data["inicio"],
                data_hora__lte=data["fim"],
            )
            .order_by("data_hora")
            .values("id", "data_hora", "tipo_ponto")
        )

        total = timedelta()
        entrada_aberta = None
        for ponto in pontos:
            if ponto["tipo_ponto"] == PunchTypeChoices.ENTRADA:
                entrada_aberta = ponto["data_hora"]
                continue
            if ponto["tipo_ponto"] == PunchTypeChoices.SAIDA and entrada_aberta is not None:
                total += ponto["data_hora"] - entrada_aberta
                entrada_aberta = None

        return Response(
            {
                "colaborador": {
                    "id": str(colaborador.id),
                    "nome": colaborador.nome,
                    "matricula": colaborador.matricula,
                },
                "periodo": {
                    "inicio": data["inicio"],
                    "fim": data["fim"],
                },
                "jornada": {
                    "id": str(colaborador.jornada_id),
                    "nome": colaborador.jornada.nome,
                    "carga_horaria_semana": colaborador.jornada.carga_horaria_semana,
                    "hora_inicio": colaborador.jornada.hora_inicio,
                    "hora_fim": colaborador.jornada.hora_fim,
                    "hora_inicio_intervalo": colaborador.jornada.hora_inicio_intervalo,
                    "hora_fim_intervalo": colaborador.jornada.hora_fim_intervalo,
                },
                "resumo": {
                    "total_segundos_trabalhados": int(total.total_seconds()),
                    "quantidade_pontos": len(pontos),
                },
                "pontos": pontos,
            }
        )


class TimeAdjustmentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TimeAdjustmentRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TimeAdjustmentRequest.objects.da_empresa(self.request.empresa).ativos().select_related(
            "colaborador",
            "ponto",
            "solicitado_por",
            "aprovado_por",
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if self.request.user.perfil == "COLABORADOR":
            queryset = queryset.filter(colaborador=self.request.user.colaborador)
        return queryset

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=["ativo", "updated_at"])

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOuMestre])
    def aprovar(self, request):
        serializer = AdjustmentApproveSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        solicitacao = serializer.save()
        return Response(
            TimeAdjustmentRequestSerializer(solicitacao, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOuMestre])
    def rejeitar(self, request):
        serializer = AdjustmentRejectSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        solicitacao = serializer.save()
        return Response(
            TimeAdjustmentRequestSerializer(solicitacao, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
