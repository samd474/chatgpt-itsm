from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("help-requests", views.HelpRequestsViewSet, basename="help-requests")
router.register("tasks", views.FulfillmentTaskViewSet, basename="tasks")
router.register("approvals", views.ApprovalViewSet, basename="approvals")
router.register("support-groups", views.SupportGroupViewSet, basename="support-groups")
router.register("categories", views.CategoryViewSet, basename="categories")
router.register("services", views.ServiceViewSet, basename="services")
router.register("ticket-templates", views.TicketTemplateViewSet, basename="ticket-templates")
router.register("queues", views.QueueViewSet, basename="queues")
router.register("technicians", views.TechnicianViewSet, basename="technicians")
router.register("people", views.PeopleViewSet, basename="people")

urlpatterns = router.urls
