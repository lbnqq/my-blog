from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.template.response import TemplateResponse
from django.urls import path, reverse

from apps.movies.services.classifier import CATEGORY_LABELS

from .models import RecommendationFeedback, RecommendationResult, SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "updated_count", "triggered_by", "started_at", "finished_at")
    list_filter = ("source", "status", "started_at")
    search_fields = ("message", "triggered_by__username")
    readonly_fields = ("source", "status", "updated_count", "message", "triggered_by", "started_at", "finished_at")

    def has_add_permission(self, request):
        return False


@admin.register(RecommendationResult)
class RecommendationResultAdmin(admin.ModelAdmin):
    list_display = ("session", "user", "category", "movie", "score", "rank_order", "algorithm_version")
    list_filter = ("algorithm_version", "session__selected_category", "session__user")
    search_fields = ("movie__title", "reason", "session__user__username")

    @admin.display(description="用户")
    def user(self, obj):
        return obj.session.user.username if obj.session.user else "游客"

    @admin.display(description="推荐分类")
    def category(self, obj):
        return CATEGORY_LABELS.get(obj.session.selected_category, obj.session.selected_category)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("movie", "session", "session__user")


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "movie",
        "rank_order",
        "rating",
        "algorithm_version",
        "updated_at",
    )
    list_filter = (
        "rating",
        "recommendation_result__session__selected_category",
        "recommendation_result__session__user",
        "recommendation_result__algorithm_version",
    )
    search_fields = (
        "recommendation_result__movie__title",
        "recommendation_result__session__user__username",
        "recommendation_result__reason",
    )
    list_select_related = (
        "recommendation_result",
        "recommendation_result__movie",
        "recommendation_result__session",
        "recommendation_result__session__user",
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "",
                self.admin_site.admin_view(self.feedback_category_directory),
                name="recommendations_recommendationfeedback_changelist",
            ),
            path(
                "category/<str:category>/",
                self.admin_site.admin_view(self.feedback_category_users),
                name="recommendation_feedback_category",
            ),
            path(
                "category/<str:category>/user/<str:user_key>/",
                self.admin_site.admin_view(self.feedback_user_list),
                name="recommendation_feedback_user",
            ),
        ]
        return custom_urls + urls

    def feedback_queryset(self):
        return RecommendationFeedback.objects.select_related(
            "recommendation_result",
            "recommendation_result__movie",
            "recommendation_result__session",
            "recommendation_result__session__user",
        )

    def feedback_category_directory(self, request):
        feedbacks = self.feedback_queryset()
        category_rows = []
        for code, label in CATEGORY_LABELS.items():
            category_feedbacks = feedbacks.filter(recommendation_result__session__selected_category=code)
            category_rows.append(
                {
                    "code": code,
                    "label": label,
                    "feedback_count": category_feedbacks.count(),
                    "user_count": (
                        category_feedbacks.order_by()
                        .values("recommendation_result__session__user_id")
                        .distinct()
                        .count()
                    ),
                    "average_rating": category_feedbacks.aggregate(avg=Avg("rating"))["avg"] or 0,
                    "url": reverse("admin:recommendation_feedback_category", args=[code]),
                }
            )
        return TemplateResponse(
            request,
            "admin/recommendations/feedback_category_directory.html",
            {
                **self.admin_site.each_context(request),
                "title": "推荐反馈分类",
                "category_rows": category_rows,
                "opts": self.model._meta,
            },
        )

    def feedback_category_users(self, request, category):
        feedbacks = self.feedback_queryset().filter(
            recommendation_result__session__selected_category=category
        )
        user_rows = []
        user_ids = (
            feedbacks.order_by()
            .values_list("recommendation_result__session__user_id", flat=True)
            .distinct()
        )
        users = get_user_model().objects.in_bulk([user_id for user_id in user_ids if user_id])
        for user_id in user_ids:
            user_feedbacks = feedbacks.filter(recommendation_result__session__user_id=user_id)
            if user_id:
                user = users.get(user_id)
                label = user.username if user else f"用户 {user_id}"
                user_key = str(user_id)
            else:
                label = "游客"
                user_key = "guest"
            user_rows.append(
                {
                    "label": label,
                    "feedback_count": user_feedbacks.count(),
                    "average_rating": user_feedbacks.aggregate(avg=Avg("rating"))["avg"] or 0,
                    "url": reverse("admin:recommendation_feedback_user", args=[category, user_key]),
                }
            )
        user_rows.sort(key=lambda row: row["label"])
        return TemplateResponse(
            request,
            "admin/recommendations/feedback_category_users.html",
            {
                **self.admin_site.each_context(request),
                "title": f"{CATEGORY_LABELS.get(category, category)} 推荐反馈用户",
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category),
                "user_rows": user_rows,
                "opts": self.model._meta,
            },
        )

    def feedback_user_list(self, request, category, user_key):
        feedbacks = self.feedback_queryset().filter(
            recommendation_result__session__selected_category=category
        )
        if user_key == "guest":
            feedbacks = feedbacks.filter(recommendation_result__session__user__isnull=True)
            user_label = "游客"
        else:
            feedbacks = feedbacks.filter(recommendation_result__session__user_id=user_key)
            user = get_user_model().objects.filter(pk=user_key).first()
            user_label = user.username if user else f"用户 {user_key}"
        feedbacks = feedbacks.order_by("-updated_at")
        return TemplateResponse(
            request,
            "admin/recommendations/feedback_user_list.html",
            {
                **self.admin_site.each_context(request),
                "title": f"{user_label} 的 {CATEGORY_LABELS.get(category, category)} 推荐反馈",
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category),
                "user_label": user_label,
                "feedbacks": feedbacks,
                "opts": self.model._meta,
            },
        )

    @admin.display(description="用户")
    def user(self, obj):
        user = obj.recommendation_result.session.user
        return user.username if user else "游客"

    @admin.display(description="推荐分类")
    def category(self, obj):
        category = obj.recommendation_result.session.selected_category
        return CATEGORY_LABELS.get(category, category)

    @admin.display(description="推荐排名")
    def rank_order(self, obj):
        return f"#{obj.recommendation_result.rank_order:02d}"

    @admin.display(description="Algorithm")
    def algorithm_version(self, obj):
        return obj.recommendation_result.algorithm_version

    @admin.display(description="Movie")
    def movie(self, obj):
        return obj.recommendation_result.movie
