from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("vendors", views.VendorViewSet, basename="vendors")
router.register("items", views.ContractViewSet, basename="contracts")

urlpatterns = router.urls
