from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UpcomingMovieNews",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("original_title", models.CharField(blank=True, max_length=160)),
                ("event_date", models.DateField()),
                ("event_label", models.CharField(max_length=40)),
                ("genre_text", models.CharField(blank=True, max_length=120)),
                ("poster_url", models.URLField(blank=True)),
                ("trailer_url", models.URLField(blank=True)),
                ("source_name", models.CharField(blank=True, max_length=80)),
                ("source_url", models.URLField(blank=True)),
                ("highlight", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "upcoming movie news",
                "verbose_name_plural": "upcoming movie news",
                "ordering": ["event_date", "sort_order", "title"],
            },
        ),
    ]
