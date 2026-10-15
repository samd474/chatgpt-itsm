from django.contrib import admin
from django.urls import include, path

from . import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live", health.live),
    path("health/ready", health.ready),
    path("api/auth/", include("accounts.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/", include("helprequests.urls")),
    path("api/", include("reports.urls")),
]
