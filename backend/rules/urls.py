from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("ticket-rules", views.TicketRuleViewSet, basename="ticket-rules")

urlpatterns = router.urls
