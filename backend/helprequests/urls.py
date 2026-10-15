from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("help-requests", views.HelpRequestsViewSet, basename="help-requests")
router.register("approvals", views.ApprovalViewSet, basename="approvals")
router.register("support-groups", views.SupportGroupViewSet, basename="support-groups")
router.register("categories", views.CategoryViewSet, basename="categories")
router.register("services", views.ServiceViewSet, basename="services")
router.register("technicians", views.TechnicianViewSet, basename="technicians")

urlpatterns = router.urls
