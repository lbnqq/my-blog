import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

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
        constraints = [
            models.UniqueConstraint(fields=["form", "movie"], name="unique_form_movie"),
        ]

    def __str__(self):
        return f"{self.form} - {self.movie}"


class UserSession(models.Model):
    CATEGORY_CHOICES = [(code, label) for code, label in CATEGORY_LABELS.items()]

    session_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    selected_category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    user_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

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
        constraints = [
            models.UniqueConstraint(fields=["session", "movie"], name="unique_session_movie_rating"),
        ]

    def __str__(self):
        return f"{self.session} {self.movie}: {self.rating}"
