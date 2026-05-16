from django.contrib import admin

from .models import RecommendationResult


@admin.register(RecommendationResult)
class RecommendationResultAdmin(admin.ModelAdmin):
    list_display = ("session", "movie", "score", "rank_order", "algorithm_version")
    list_filter = ("algorithm_version",)
    search_fields = ("movie__title", "reason")
