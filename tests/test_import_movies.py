from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.movies.models import Movie
from apps.ratings.models import RatingForm, RatingFormMovie


class ImportMoviesTests(TestCase):
    def test_import_movies_creates_movies_forms_and_links(self):
        sample_path = Path("data/samples/sample_movies.csv")

        call_command("import_movies", str(sample_path))

        self.assertGreaterEqual(Movie.objects.count(), 25)
        self.assertEqual(RatingForm.objects.count(), 5)
        self.assertGreater(RatingFormMovie.objects.count(), 0)
        movie = Movie.objects.get(title="盗梦空间")
        self.assertEqual(movie.main_category, "suspense_crime")
        self.assertIn("悬疑", movie.feature_tags)
