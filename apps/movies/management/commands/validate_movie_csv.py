import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.movies.services.classifier import CATEGORY_LABELS, normalize_category


REQUIRED_HEADERS = [
    "douban_id",
    "title",
    "original_title",
    "year",
    "directors",
    "actors",
    "genres",
    "countries",
    "rating",
    "rating_count",
    "rank",
    "poster_url",
    "summary",
    "main_category",
    "feature_tags",
]


class Command(BaseCommand):
    help = "Validate Douban Top1000 CSV data before importing it."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument(
            "--expect-count",
            type=int,
            default=1000,
            help="Expected number of non-empty movie rows. Defaults to 1000.",
        )
        parser.add_argument(
            "--allow-draft",
            action="store_true",
            help="Allow blank draft rows while checking headers and filled rows.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        errors = []
        warnings = []
        rows = self.read_rows(csv_path, errors)
        if errors:
            self.raise_errors(errors)

        allow_draft = options["allow_draft"]
        filled_rows = [row for row in rows if self.is_filled_row(row)]

        if not allow_draft and len(filled_rows) != options["expect_count"]:
            errors.append(
                f"Expected {options['expect_count']} filled movie rows, found {len(filled_rows)}."
            )

        self.validate_rows(filled_rows, errors, warnings)
        self.validate_category_balance(filled_rows, warnings)

        if errors:
            self.raise_errors(errors)

        for warning in warnings:
            self.stdout.write(self.style.WARNING(warning))

        self.stdout.write(
            self.style.SUCCESS(
                f"CSV validation passed: {len(filled_rows)} filled rows checked."
            )
        )

    def read_rows(self, csv_path, errors):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            headers = reader.fieldnames or []
            missing_headers = [header for header in REQUIRED_HEADERS if header not in headers]
            extra_headers = [header for header in headers if header not in REQUIRED_HEADERS]

            if missing_headers:
                errors.append(f"Missing headers: {', '.join(missing_headers)}")
            if extra_headers:
                errors.append(f"Unknown headers: {', '.join(extra_headers)}")
            if errors:
                return []

            return list(reader)

    def validate_rows(self, rows, errors, warnings):
        seen_douban_ids = {}
        seen_title_year = {}
        seen_ranks = {}

        for index, row in enumerate(rows, start=2):
            title = row.get("title", "").strip()
            douban_id = row.get("douban_id", "").strip()
            year = row.get("year", "").strip()
            rank = row.get("rank", "").strip()
            category = row.get("main_category", "").strip()

            if not title:
                errors.append(f"Row {index}: title is required.")
            if not row.get("genres", "").strip():
                errors.append(f"Row {index}: genres is required.")
            if not row.get("rating", "").strip():
                errors.append(f"Row {index}: rating is required.")

            self.validate_int(row, "year", index, errors, min_value=1888, max_value=2100, required=False)
            self.validate_int(row, "rating_count", index, errors, min_value=0, required=False)
            self.validate_int(row, "rank", index, errors, min_value=1, max_value=1000, required=True)
            self.validate_rating(row, index, errors)

            if category and not self.is_valid_category(category):
                errors.append(
                    f"Row {index}: main_category must be one of {', '.join(CATEGORY_LABELS)}."
                )
            if not category:
                warnings.append(f"Row {index}: main_category is blank; importer will infer it from genres.")

            if douban_id:
                if douban_id in seen_douban_ids:
                    errors.append(f"Row {index}: duplicate douban_id also appears on row {seen_douban_ids[douban_id]}.")
                seen_douban_ids[douban_id] = index

            title_year_key = (title, year)
            if title and year:
                if title_year_key in seen_title_year:
                    errors.append(
                        f"Row {index}: duplicate title + year also appears on row {seen_title_year[title_year_key]}."
                    )
                seen_title_year[title_year_key] = index

            if rank:
                if rank in seen_ranks:
                    errors.append(f"Row {index}: duplicate rank also appears on row {seen_ranks[rank]}.")
                seen_ranks[rank] = index

    def validate_int(self, row, field_name, index, errors, min_value=None, max_value=None, required=False):
        value = row.get(field_name, "").strip()
        if not value:
            if required:
                errors.append(f"Row {index}: {field_name} is required.")
            return
        try:
            number = int(value)
        except ValueError:
            errors.append(f"Row {index}: {field_name} must be an integer.")
            return
        if min_value is not None and number < min_value:
            errors.append(f"Row {index}: {field_name} must be >= {min_value}.")
        if max_value is not None and number > max_value:
            errors.append(f"Row {index}: {field_name} must be <= {max_value}.")

    def validate_rating(self, row, index, errors):
        value = row.get("rating", "").strip()
        if not value:
            return
        try:
            rating = float(value)
        except ValueError:
            errors.append(f"Row {index}: rating must be a number.")
            return
        if rating < 0 or rating > 10:
            errors.append(f"Row {index}: rating must be between 0 and 10.")

    def validate_category_balance(self, rows, warnings):
        counts = {code: 0 for code in CATEGORY_LABELS}
        for row in rows:
            category = row.get("main_category", "").strip()
            if category:
                counts[normalize_category(category)] += 1

        for category, count in counts.items():
            if count and count < 20:
                warnings.append(
                    f"Category {category} has only {count} filled rows; rating forms work best with at least 20."
                )

    def is_filled_row(self, row):
        return any(str(value).strip() for value in row.values())

    def is_valid_category(self, value):
        return value in CATEGORY_LABELS or value in CATEGORY_LABELS.values()

    def raise_errors(self, errors):
        preview = "\n".join(errors[:30])
        remaining = len(errors) - 30
        if remaining > 0:
            preview += f"\n... and {remaining} more errors."
        raise CommandError(preview)
