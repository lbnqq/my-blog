from django.contrib import admin
from django.urls import include, path

from apps.admin_order import apply_admin_ordering


apply_admin_ordering(admin.site)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("agent/", include("apps.agent.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("analytics/", include("apps.recommendations.urls")),
    path("", include("apps.blog.urls")),
    path("movies/", include("apps.movies.urls")),
    path("recommend/", include("apps.ratings.urls")),
]
