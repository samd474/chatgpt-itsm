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
]

admin_urlpatterns = router.urls
