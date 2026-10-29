from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("articles", views.ArticleViewSet, basename="articles")

urlpatterns = router.urls
