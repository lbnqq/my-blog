from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("movies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RatingForm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("suspense_crime", "悬疑犯罪"),
                            ("romance_drama", "爱情剧情"),
                            ("comedy_animation", "喜剧动画"),
                            ("sci_fi_action", "科幻动作冒险"),
                            ("history_war_biography", "历史战争传记"),
                        ],
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["category"]},
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "selected_category",
                    models.CharField(
                        choices=[
                            ("suspense_crime", "悬疑犯罪"),
                            ("romance_drama", "爱情剧情"),
                            ("comedy_animation", "喜剧动画"),
                            ("sci_fi_action", "科幻动作冒险"),
                            ("history_war_biography", "历史战争传记"),
                        ],
                        max_length=32,
                    ),
                ),
                ("user_id", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RatingFormMovie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_required", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "form",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="form_movies", to="ratings.ratingform"),
                ),
                (
                    "movie",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rating_form_links", to="movies.movie"),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="UserRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "movie",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_ratings", to="movies.movie"),
                ),
                (
                    "session",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="ratings.usersession"),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="ratingformmovie",
            constraint=models.UniqueConstraint(fields=("form", "movie"), name="unique_form_movie"),
        ),
        migrations.AddConstraint(
            model_name="userrating",
            constraint=models.UniqueConstraint(fields=("session", "movie"), name="unique_session_movie_rating"),
        ),
    ]
