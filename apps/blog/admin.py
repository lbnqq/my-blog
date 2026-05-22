from django.contrib import admin

from .models import DoubanChartMovie, DoubanWeeklyReputationMovie, UpcomingMovieNews


@admin.register(DoubanChartMovie)
class DoubanChartMovieAdmin(admin.ModelAdmin):
    list_display = ("rank", "title", "rating", "rating_count", "is_active", "fetched_at")
    list_filter = ("is_active", "fetched_at")
    search_fields = ("title", "subtitle", "douban_id")
    ordering = ("rank", "title")


@admin.register(DoubanWeeklyReputationMovie)
class DoubanWeeklyReputationMovieAdmin(admin.ModelAdmin):
    list_display = ("rank", "title", "rating", "rating_count", "is_active", "fetched_at")
    list_filter = ("is_active", "fetched_at")
    search_fields = ("title", "subtitle", "douban_id")
    ordering = ("rank", "title")


@admin.register(UpcomingMovieNews)
class UpcomingMovieNewsAdmin(admin.ModelAdmin):
    list_display = ("title", "content_type", "region", "event_date", "event_label", "is_active", "sort_order")
    list_filter = ("content_type", "region", "is_active", "event_date")
    search_fields = ("title", "original_title", "highlight")
    ordering = ("content_type", "region", "event_date", "sort_order", "title")
