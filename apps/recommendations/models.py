from django.db import models

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
        constraints = [
            models.UniqueConstraint(fields=["session", "movie"], name="unique_result_movie"),
            models.UniqueConstraint(fields=["session", "rank_order"], name="unique_result_rank"),
        ]

    def __str__(self):
        return f"{self.rank_order}. {self.movie}"
