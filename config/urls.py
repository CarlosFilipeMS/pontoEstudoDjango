from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from workforce.auth import TenantTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TenantTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/workforce/", include("workforce.urls")),
    path("api/attendance/", include("attendance.urls")),
]
