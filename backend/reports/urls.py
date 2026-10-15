from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("audit", views.AuditEventViewSet, basename="audit")
router.register("imports", views.ImportJobViewSet, basename="imports")

urlpatterns = [
    path("reports/service-desk/", views.service_desk_report),
    *router.urls,
]
