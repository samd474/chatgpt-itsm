from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("items", views.AssetViewSet, basename="assets")
router.register("types", views.AssetTypeViewSet, basename="asset-types")
router.register("locations", views.LocationViewSet, basename="locations")

urlpatterns = router.urls
