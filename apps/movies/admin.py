from django.contrib import admin

from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "main_category", "rating", "rank")
    list_filter = ("main_category", "year")
    search_fields = ("title", "original_title", "douban_id")
