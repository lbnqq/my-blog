from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("movies", "0001_initial"),
        ("ratings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.FloatField()),
                ("rank_order", models.PositiveSmallIntegerField()),
                ("reason", models.TextField()),
                ("algorithm_version", models.CharField(default="taskcf_v1", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "movie",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_results", to="movies.movie"),
                ),
                (
                    "session",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_results", to="ratings.usersession"),
                ),
            ],
            options={"ordering": ["rank_order"]},
        ),
        migrations.AddConstraint(
            model_name="recommendationresult",
            constraint=models.UniqueConstraint(fields=("session", "movie"), name="unique_result_movie"),
        ),
        migrations.AddConstraint(
            model_name="recommendationresult",
            constraint=models.UniqueConstraint(fields=("session", "rank_order"), name="unique_result_rank"),
        ),
    ]
