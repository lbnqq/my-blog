from django.contrib import admin

from .models import RatingForm, RatingFormMovie, UserRating, UserSession


class RatingFormMovieInline(admin.TabularInline):
    model = RatingFormMovie
    extra = 0


@admin.register(RatingForm)
class RatingFormAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active")
    inlines = [RatingFormMovieInline]


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "selected_category", "created_at", "completed_at")
    list_filter = ("selected_category",)


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ("session", "movie", "rating", "created_at")
    list_filter = ("rating",)
