from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Movie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("douban_id", models.CharField(blank=True, db_index=True, max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("original_title", models.CharField(blank=True, max_length=255)),
                ("year", models.PositiveIntegerField(blank=True, null=True)),
                ("directors", models.JSONField(blank=True, default=list)),
                ("actors", models.JSONField(blank=True, default=list)),
                ("genres", models.JSONField(blank=True, default=list)),
                ("countries", models.JSONField(blank=True, default=list)),
                (
                    "rating",
                    models.DecimalField(
                        decimal_places=1,
                        max_digits=3,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                ("rating_count", models.PositiveIntegerField(default=0)),
                ("rank", models.PositiveIntegerField(blank=True, null=True)),
                ("poster_url", models.URLField(blank=True)),
                ("summary", models.TextField(blank=True)),
                (
                    "main_category",
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
                ("feature_tags", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["rank", "-rating", "title"]},
        ),
        migrations.AddConstraint(
            model_name="movie",
            constraint=models.UniqueConstraint(
                condition=~models.Q(douban_id=""),
                fields=("douban_id",),
                name="unique_movie_douban_id",
            ),
        ),
        migrations.AddConstraint(
            model_name="movie",
            constraint=models.UniqueConstraint(fields=("title", "year"), name="unique_movie_title_year"),
        ),
    ]
