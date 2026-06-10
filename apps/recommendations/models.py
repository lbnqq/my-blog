from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

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
