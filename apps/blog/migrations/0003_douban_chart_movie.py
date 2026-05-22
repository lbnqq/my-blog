from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_upcoming_movie_news_type_region"),
    ]

    operations = [
        migrations.CreateModel(
            name="DoubanChartMovie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("douban_id", models.CharField(db_index=True, max_length=32, unique=True)),
                ("rank", models.PositiveIntegerField(db_index=True)),
                ("title", models.CharField(max_length=255)),
                ("subtitle", models.CharField(blank=True, max_length=255)),
                ("info_text", models.TextField(blank=True)),
                ("rating", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("rating_count", models.PositiveIntegerField(default=0)),
                ("poster_url", models.URLField(blank=True)),
                ("subject_url", models.URLField()),
                ("fetched_at", models.DateTimeField(db_index=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "douban chart movie",
                "verbose_name_plural": "douban chart movies",
                "ordering": ["rank", "title"],
            },
        ),
    ]
