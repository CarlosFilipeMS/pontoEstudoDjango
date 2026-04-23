from django.urls import include, path
from rest_framework.routers import DefaultRouter

from attendance.views import TimeAdjustmentRequestViewSet, TimeEntryViewSet

router = DefaultRouter()
router.register("pontos", TimeEntryViewSet, basename="pontos")
router.register("solicitacoes-ajuste", TimeAdjustmentRequestViewSet, basename="solicitacoes-ajuste")

urlpatterns = [
    path("", include(router.urls)),
]
