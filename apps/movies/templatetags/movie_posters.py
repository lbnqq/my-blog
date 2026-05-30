from pathlib import Path
from urllib.parse import urlparse

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.urls import reverse


register = template.Library()


def poster_extension(movie):
    parsed = urlparse(movie.poster_url or "")
    suffix = Path(parsed.path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def cached_poster_relative_path(movie):
    if not movie or not movie.douban_id:
        return ""
    return f"img/posters/{movie.douban_id}{poster_extension(movie)}"


@register.filter
def cached_poster_url(movie):
    relative_path = cached_poster_relative_path(movie)
    if not relative_path:
        return ""
    if finders.find(relative_path):
        return static(relative_path)
    if movie.poster_url:
        return reverse("movies:poster", args=[movie.pk])
    return ""


def poster_cache_path(movie):
    relative_path = cached_poster_relative_path(movie)
    if not relative_path:
        return None
    static_dir = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.BASE_DIR / "static"
    return Path(static_dir) / relative_path
