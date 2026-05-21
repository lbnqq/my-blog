from django.contrib import admin

from .models import UpcomingMovieNews


@admin.register(UpcomingMovieNews)
class UpcomingMovieNewsAdmin(admin.ModelAdmin):
    list_display = ("title", "content_type", "region", "event_date", "event_label", "is_active", "sort_order")
    list_filter = ("content_type", "region", "is_active", "event_date")
    search_fields = ("title", "original_title", "highlight")
    ordering = ("content_type", "region", "event_date", "sort_order", "title")
