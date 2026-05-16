from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.movies.services.classifier import CATEGORY_LABELS


class Movie(models.Model):
    CATEGORY_CHOICES = [(code, label) for code, label in CATEGORY_LABELS.items()]

    douban_id = models.CharField(max_length=32, blank=True, db_index=True)
    title = models.CharField(max_length=255)
    original_title = models.CharField(max_length=255, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    directors = models.JSONField(default=list, blank=True)
    actors = models.JSONField(default=list, blank=True)
    genres = models.JSONField(default=list, blank=True)
    countries = models.JSONField(default=list, blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    rating_count = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    poster_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    main_category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    feature_tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "-rating", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["douban_id"],
                condition=~models.Q(douban_id=""),
                name="unique_movie_douban_id",
            ),
            models.UniqueConstraint(
                fields=["title", "year"],
                name="unique_movie_title_year",
            ),
        ]

    def __str__(self):
        return self.title
