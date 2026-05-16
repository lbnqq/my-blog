import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from apps.movies.management.commands.validate_movie_csv import REQUIRED_HEADERS
from apps.movies.models import Movie
from apps.ratings.models import RatingForm, RatingFormMovie


class ImportMoviesTests(TestCase):
    def test_import_movies_creates_movies_forms_and_links(self):
        sample_path = Path("data/samples/sample_movies.csv")

        call_command("import_movies", str(sample_path))

        self.assertGreaterEqual(Movie.objects.count(), 25)
        self.assertEqual(RatingForm.objects.count(), 5)
        self.assertGreater(RatingFormMovie.objects.count(), 0)
        movie = Movie.objects.get(douban_id="3541415")
        self.assertEqual(movie.main_category, "suspense_crime")
        self.assertIn("悬疑", movie.feature_tags)

    def test_import_movies_updates_existing_title_year_when_douban_id_is_new(self):
        Movie.objects.create(
            douban_id="old-id",
            title="Same Movie",
            year=1994,
            directors=[],
            actors=[],
            genres=["剧情"],
            countries=[],
            rating=8.0,
            rating_count=100,
            rank=99,
            poster_url="",
            summary="Old summary.",
            main_category="romance_drama",
            feature_tags=["剧情"],
        )
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "same_movie.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=REQUIRED_HEADERS)
                writer.writeheader()
                writer.writerow(
                    {
                        "douban_id": "1292052",
                        "title": "Same Movie",
                        "original_title": "",
                        "year": "1994",
                        "directors": "Director",
                        "actors": "Actor",
                        "genres": "剧情;犯罪",
                        "countries": "美国",
                        "rating": "9.7",
                        "rating_count": "3000000",
                        "rank": "1",
                        "poster_url": "",
                        "summary": "New summary.",
                        "main_category": "suspense_crime",
                        "feature_tags": "剧情;犯罪;高分",
                    }
                )

            call_command("import_movies", str(csv_path))

        self.assertEqual(Movie.objects.count(), 1)
        movie = Movie.objects.get(title="Same Movie", year=1994)
        self.assertEqual(movie.douban_id, "1292052")
        self.assertEqual(movie.rating_count, 3000000)
        self.assertEqual(movie.main_category, "suspense_crime")
