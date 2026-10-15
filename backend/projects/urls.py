from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("items", views.ProjectViewSet, basename="projects")
router.register("milestones", views.MilestoneViewSet, basename="milestones")
router.register("tasks", views.ProjectTaskViewSet, basename="project-tasks")

urlpatterns = router.urls
