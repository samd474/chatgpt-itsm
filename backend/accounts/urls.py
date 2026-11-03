from django.urls import path
from rest_framework.routers import DefaultRouter

from . import admin_api, views

router = DefaultRouter()
router.register("users", admin_api.UserAdminViewSet, basename="admin-users")
router.register("roles", admin_api.RoleViewSet, basename="admin-roles")

urlpatterns = [
    path("csrf/", views.csrf),
    path("login/", views.login_view),
    path("logout/", views.logout_view),
    path("me/", views.me),
    path("2fa/", views.two_factor_status),
    path("2fa/verify/", views.two_factor_verify),
    path("2fa/setup/", views.two_factor_setup),
    path("2fa/confirm/", views.two_factor_confirm),
    path("2fa/recovery-codes/", views.two_factor_recovery_codes),
    path("2fa/disable/", views.two_factor_disable),
]

admin_urlpatterns = router.urls
