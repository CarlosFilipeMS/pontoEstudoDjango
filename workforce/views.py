from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdminOuMestre
from workforce.models import Collaborator, User, WorkSchedule
from workforce.services import AdminManagementService
from workforce.serializers import CollaboratorSerializer, UserSerializer, WorkScheduleSerializer


class WorkScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated, IsAdminOuMestre]

    def get_queryset(self):
        return WorkSchedule.objects.da_empresa(self.request.empresa).ativos()

    def perform_create(self, serializer):
        serializer.save(empresa_id=self.request.empresa.id)

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=["ativo", "updated_at"])


class CollaboratorViewSet(viewsets.ModelViewSet):
    serializer_class = CollaboratorSerializer
    permission_classes = [IsAuthenticated, IsAdminOuMestre]

    def get_queryset(self):
        return Collaborator.objects.da_empresa(self.request.empresa).ativos().select_related("jornada")

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=["ativo", "updated_at"])


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminOuMestre]

    def get_queryset(self):
        return User.objects.da_empresa(self.request.empresa).ativos().select_related("colaborador")

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOuMestre])
    def promover_admin(self, request, pk=None):
        alvo = self.get_object()
        alvo = AdminManagementService.promover_para_admin(solicitante=request.user, alvo=alvo)
        return Response(UserSerializer(alvo).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminOuMestre])
    def rebaixar_admin(self, request, pk=None):
        alvo = self.get_object()
        alvo = AdminManagementService.rebaixar_admin(solicitante=request.user, alvo=alvo)
        return Response(UserSerializer(alvo).data, status=status.HTTP_200_OK)
