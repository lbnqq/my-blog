import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.movies.management.commands.validate_movie_csv import REQUIRED_HEADERS


class ValidateMovieCsvTests(TestCase):
    def write_csv(self, rows):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        csv_path = Path(temp_dir.name) / "movies.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=REQUIRED_HEADERS)
            writer.writeheader()
            writer.writerows(rows)
        return csv_path

    def valid_row(self, **overrides):
        row = {
            "douban_id": "1292052",
            "title": "Movie Title",
            "original_title": "Original Movie Title",
            "year": "1994",
            "directors": "Director A",
            "actors": "Actor A;Actor B",
            "genres": "剧情;犯罪",
            "countries": "美国",
            "rating": "9.7",
            "rating_count": "3000000",
            "rank": "1",
            "poster_url": "",
            "summary": "A short summary.",
            "main_category": "suspense_crime",
            "feature_tags": "剧情;犯罪;高分",
        }
        row.update(overrides)
        return row

    def test_validates_complete_rows(self):
        csv_path = self.write_csv([self.valid_row()])

        call_command("validate_movie_csv", str(csv_path), expect_count=1)

    def test_rejects_duplicate_rank(self):
        csv_path = self.write_csv(
            [
                self.valid_row(),
                self.valid_row(douban_id="1292720", title="Another Movie", rank="1"),
            ]
        )

        with self.assertRaises(CommandError) as error:
            call_command("validate_movie_csv", str(csv_path), expect_count=2)

        self.assertIn("duplicate rank", str(error.exception))

    def test_allows_blank_draft_template(self):
        csv_path = self.write_csv([{}])

        call_command("validate_movie_csv", str(csv_path), allow_draft=True)
