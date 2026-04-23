from django.urls import include, path
from rest_framework.routers import DefaultRouter

from workforce.views import CollaboratorViewSet, UserViewSet, WorkScheduleViewSet

router = DefaultRouter()
router.register("jornadas", WorkScheduleViewSet, basename="jornadas")
router.register("colaboradores", CollaboratorViewSet, basename="colaboradores")
router.register("usuarios", UserViewSet, basename="usuarios")

urlpatterns = [
    path("", include(router.urls)),
]
