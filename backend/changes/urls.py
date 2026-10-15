from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("items", views.ChangeRequestViewSet, basename="changes")
router.register("approvals", views.ChangeApprovalViewSet, basename="change-approvals")

urlpatterns = router.urls
