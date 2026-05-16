import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS, classify_main_category, normalize_category
from apps.movies.services.feature_builder import build_feature_tags, split_semicolon_text
from apps.ratings.models import RatingForm, RatingFormMovie


class Command(BaseCommand):
    help = "Import Douban Top1000-style movie CSV data."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        imported = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                movie = self.import_row(row)
                imported += 1
                self.link_rating_form(movie)

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} movies."))

    def import_row(self, row):
        genres = split_semicolon_text(row.get("genres"))
        directors = split_semicolon_text(row.get("directors"))
        actors = split_semicolon_text(row.get("actors"))
        countries = split_semicolon_text(row.get("countries"))
        explicit_category = row.get("main_category", "").strip()
        main_category = normalize_category(explicit_category) if explicit_category else classify_main_category(genres)
        feature_tags = build_feature_tags(
            row.get("feature_tags"),
            genres,
            directors[:1],
            countries,
        )

        defaults = {
            "original_title": row.get("original_title", "").strip(),
            "year": int(row["year"]) if row.get("year") else None,
            "directors": directors,
            "actors": actors,
            "genres": genres,
            "countries": countries,
            "rating": row.get("rating") or 0,
            "rating_count": int(row["rating_count"]) if row.get("rating_count") else 0,
            "rank": int(row["rank"]) if row.get("rank") else None,
            "poster_url": row.get("poster_url", "").strip(),
            "summary": row.get("summary", "").strip(),
            "main_category": main_category,
            "feature_tags": feature_tags,
        }

        douban_id = row.get("douban_id", "").strip()
        title = row.get("title", "").strip()
        if not title:
            raise CommandError("Movie title is required.")

        if douban_id:
            movie, _created = Movie.objects.update_or_create(
                douban_id=douban_id,
                defaults={"title": title, **defaults},
            )
            return movie

        movie, _created = Movie.objects.update_or_create(
            title=title,
            year=defaults["year"],
            defaults=defaults,
        )
        return movie

    def link_rating_form(self, movie):
        form, _created = RatingForm.objects.get_or_create(
            category=movie.main_category,
            defaults={
                "title": f"{CATEGORY_LABELS[movie.main_category]}电影评分表",
                "description": f"根据你对{CATEGORY_LABELS[movie.main_category]}类电影的评分生成推荐。",
            },
        )
        current_count = form.form_movies.count()
        if current_count < 20:
            RatingFormMovie.objects.get_or_create(
                form=form,
                movie=movie,
                defaults={"sort_order": current_count + 1, "is_required": current_count < 8},
            )
