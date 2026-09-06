from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings

from apps.admin_labels import bilingual_label
from apps.movies.models import Movie
from apps.ratings.models import UserSession


class RecommendationResult(models.Model):
    session = models.ForeignKey(
        UserSession,
        on_delete=models.CASCADE,
        related_name="recommendation_results",
    )
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name="recommendation_results",
    )
    score = models.FloatField()
    rank_order = models.PositiveSmallIntegerField()
    reason = models.TextField()
    algorithm_version = models.CharField(max_length=32, default="taskcf_v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["rank_order"]
        verbose_name = bilingual_label("推荐结果", "Recommendation Result")
        verbose_name_plural = bilingual_label("推荐结果", "Recommendation Results")
        constraints = [
            models.UniqueConstraint(fields=["session", "movie"], name="unique_result_movie"),
            models.UniqueConstraint(fields=["session", "rank_order"], name="unique_result_rank"),
        ]

    def __str__(self):
        return f"{self.rank_order}. {self.movie}"


class RecommendationFeedback(models.Model):
    recommendation_result = models.OneToOneField(
        RecommendationResult,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = bilingual_label("推荐反馈", "Recommendation Feedback")
        verbose_name_plural = bilingual_label("推荐反馈", "Recommendation Feedback")

    def __str__(self):
        return f"{self.recommendation_result}: {self.rating}"


class SyncRun(models.Model):
    class Source(models.TextChoices):
        DOUBAN_CHART = "douban_chart", "豆瓣电影排行榜"
        WEEKLY_REPUTATION = "weekly_reputation", "豆瓣一周口碑榜"

    class Status(models.TextChoices):
        RUNNING = "running", "执行中"
        SUCCESS = "success", "成功"
        SKIPPED = "skipped", "已跳过"
        FAILED = "failed", "失败"

    source = models.CharField(max_length=32, choices=Source.choices, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    updated_count = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="analytics_sync_runs",
    )

    class Meta:
        ordering = ["-started_at"]
        verbose_name = bilingual_label("数据同步记录", "Data Sync Run")
        verbose_name_plural = bilingual_label("数据同步记录", "Data Sync Runs")

    def __str__(self):
        return f"{self.get_source_display()} - {self.get_status_display()}"
