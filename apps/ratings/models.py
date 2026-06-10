import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.admin_labels import bilingual_label
from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS


class RatingForm(models.Model):
    CATEGORY_CHOICES = [(code, label) for code, label in CATEGORY_LABELS.items()]

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category"]
        verbose_name = bilingual_label("评分表", "Rating Form")
        verbose_name_plural = bilingual_label("评分表", "Rating Forms")

    def __str__(self):
        return self.title


class RatingFormMovie(models.Model):
    form = models.ForeignKey(RatingForm, on_delete=models.CASCADE, related_name="form_movies")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="rating_form_links")
    sort_order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = bilingual_label("评分表电影", "Rating Form Movie")
        verbose_name_plural = bilingual_label("评分表电影", "Rating Form Movies")
        constraints = [
            models.UniqueConstraint(fields=["form", "movie"], name="unique_form_movie"),
        ]

    def __str__(self):
        return f"{self.form} - {self.movie}"


class UserSession(models.Model):
    CATEGORY_CHOICES = [(code, label) for code, label in CATEGORY_LABELS.items()]

    session_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    selected_category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rating_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = bilingual_label("用户推荐会话", "User Recommendation Session")
        verbose_name_plural = bilingual_label("用户推荐会话", "User Recommendation Sessions")

    def __str__(self):
        return str(self.session_key)


class UserRating(models.Model):
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name="ratings")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="user_ratings")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = bilingual_label("用户偏好评分", "User Preference Rating")
        verbose_name_plural = bilingual_label("用户偏好评分", "User Preference Ratings")
        constraints = [
            models.UniqueConstraint(fields=["session", "movie"], name="unique_session_movie_rating"),
        ]

    def __str__(self):
        return f"{self.session} {self.movie}: {self.rating}"
