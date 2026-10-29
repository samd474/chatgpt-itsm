from django.contrib import admin
from django.urls import include, path

from core.urls import admin_patterns, public_patterns

from . import health

admin.site.site_header = "ITSM administration"
admin.site.site_title = "ITSM administration"
admin.site.index_title = "Configuration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live", health.live),
    path("health/ready", health.ready),
    path("api/auth/", include("accounts.urls")),
    path("api/admin/", include(admin_patterns)),
    path("api/catalog/", include("catalog.urls")),
    path("api/assets/", include("assets.urls")),
    path("api/contracts/", include("contracts.urls")),
    path("api/projects/", include("projects.urls")),
    path("api/changes/", include("changes.urls")),
    path("api/solutions/", include("solutions.urls")),
    path("api/rules/", include("rules.urls")),
    path("api/", include(public_patterns)),
    path("api/", include("helprequests.urls")),
    path("api/", include("reports.urls")),
]
