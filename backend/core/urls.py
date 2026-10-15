from django.urls import path
from rest_framework.routers import DefaultRouter

from accounts.urls import admin_urlpatterns
from alerts.views import NotificationTemplateViewSet
from catalog.views import CatalogItemAdminViewSet
from slas.views import BusinessCalendarViewSet, SLAPolicyViewSet

from .views import CustomFieldDefinitionViewSet

admin_router = DefaultRouter()
admin_router.register("notification-templates", NotificationTemplateViewSet, basename="notification-templates")
admin_router.register("catalog-items", CatalogItemAdminViewSet, basename="admin-catalog-items")
admin_router.register("sla-policies", SLAPolicyViewSet, basename="sla-policies")
admin_router.register("business-calendars", BusinessCalendarViewSet, basename="business-calendars")

public_router = DefaultRouter()
public_router.register("custom-fields", CustomFieldDefinitionViewSet, basename="custom-fields")

# Mounted at /api/admin/
admin_patterns = [*admin_urlpatterns, *admin_router.urls]
# Mounted at /api/
public_patterns = public_router.urls
