from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("recommendations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationFeedback",
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
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "recommendation_result",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="recommendations.recommendationresult",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
    ]
