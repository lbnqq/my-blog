from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.blog.urls")),
    path("recommend/", include("apps.ratings.urls")),
]
