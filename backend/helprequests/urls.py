from rest_framework.routers import DefaultRouter
from .views import HelpRequestsViewSet

router = DefaultRouter()
router.register("help-requests", HelpRequestsViewSet, basename="help-requests")

urlpatterns = router.urls
