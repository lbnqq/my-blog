import datetime
import json
from pathlib import Path

from django.test import TestCase
from django.utils import timezone


class UpcomingMovieNewsTests(TestCase):
    def test_homepage_upcoming_groups_limit_each_region_to_three_items(self):
        from apps.blog.models import UpcomingMovieNews
        from apps.blog.services.upcoming_news import get_homepage_upcoming_groups

        today = timezone.localdate()
        for index in range(4):
            UpcomingMovieNews.objects.create(
                title=f"Domestic {index}",
                event_date=today + datetime.timedelta(days=index),
                event_label="Coming soon",
                highlight="Short highlight.",
                is_active=True,
                region=UpcomingMovieNews.Region.DOMESTIC,
                sort_order=index,
            )
            UpcomingMovieNews.objects.create(
                title=f"Foreign {index}",
                event_date=today + datetime.timedelta(days=index),
                event_label="Coming soon",
                highlight="Short highlight.",
                is_active=True,
                region=UpcomingMovieNews.Region.FOREIGN,
                sort_order=index,
            )

        domestic, foreign = get_homepage_upcoming_groups(today=today, per_region=3)

        self.assertEqual([item.title for item in domestic], ["Domestic 0", "Domestic 1", "Domestic 2"])
        self.assertEqual([item.title for item in foreign], ["Foreign 0", "Foreign 1", "Foreign 2"])

    def test_homepage_upcoming_groups_ignore_inactive_and_fall_back_after_next_seven_days(self):
        from apps.blog.models import UpcomingMovieNews
        from apps.blog.services.upcoming_news import get_homepage_upcoming_groups

        today = timezone.localdate()
        UpcomingMovieNews.objects.create(
            title="Inactive",
            event_date=today + datetime.timedelta(days=1),
            event_label="Coming soon",
            highlight="Hidden item.",
            is_active=False,
            region=UpcomingMovieNews.Region.DOMESTIC,
        )
        this_week = UpcomingMovieNews.objects.create(
            title="This Week",
            event_date=today + datetime.timedelta(days=2),
            event_label="Coming soon",
            highlight="Shown first.",
            is_active=True,
            region=UpcomingMovieNews.Region.DOMESTIC,
        )
        later = UpcomingMovieNews.objects.create(
            title="Later",
            event_date=today + datetime.timedelta(days=12),
            event_label="Coming soon",
            highlight="Fallback item.",
            is_active=True,
            region=UpcomingMovieNews.Region.DOMESTIC,
        )

        domestic, foreign = get_homepage_upcoming_groups(today=today, per_region=3)

        self.assertEqual(domestic, [this_week, later])
        self.assertEqual(foreign, [])

    def test_homepage_upcoming_groups_fill_with_recent_past_items_when_future_items_are_sparse(self):
        from apps.blog.models import UpcomingMovieNews
        from apps.blog.services.upcoming_news import get_homepage_upcoming_groups

        today = timezone.localdate()
        past = UpcomingMovieNews.objects.create(
            title="Yesterday Trailer",
            event_date=today - datetime.timedelta(days=1),
            event_label="本周上映",
            highlight="Recent past item should still keep the section full.",
            is_active=True,
            region=UpcomingMovieNews.Region.DOMESTIC,
        )
        future = UpcomingMovieNews.objects.create(
            title="Future Trailer",
            event_date=today + datetime.timedelta(days=2),
            event_label="即将上映",
            highlight="Future item should stay first.",
            is_active=True,
            region=UpcomingMovieNews.Region.DOMESTIC,
        )

        domestic, _foreign = get_homepage_upcoming_groups(today=today, per_region=3)

        self.assertEqual(domestic, [future, past])

    def test_homepage_now_showing_uses_active_now_showing_items_only(self):
        from apps.blog.models import UpcomingMovieNews
        from apps.blog.services.upcoming_news import get_homepage_now_showing

        today = timezone.localdate()
        UpcomingMovieNews.objects.create(
            title="Upcoming Hidden",
            event_date=today + datetime.timedelta(days=1),
            event_label="Coming soon",
            highlight="Not a now showing item.",
            is_active=True,
            content_type=UpcomingMovieNews.ContentType.UPCOMING,
        )
        UpcomingMovieNews.objects.create(
            title="Inactive Showing",
            event_date=today,
            event_label="正在热映",
            highlight="Hidden inactive item.",
            is_active=False,
            content_type=UpcomingMovieNews.ContentType.NOW_SHOWING,
        )
        for index in range(7):
            UpcomingMovieNews.objects.create(
                title=f"Showing {index}",
                event_date=today - datetime.timedelta(days=index),
                event_label="正在热映",
                highlight="A theater highlight.",
                is_active=True,
                content_type=UpcomingMovieNews.ContentType.NOW_SHOWING,
                sort_order=index,
            )

        results = list(get_homepage_now_showing(today=today, limit=6))

        self.assertEqual(len(results), 6)
        self.assertEqual([item.title for item in results], [f"Showing {index}" for index in range(6)])

    def test_demo_fixture_homepage_items_include_clickable_sources(self):
        fixture_path = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "upcoming_movie_news.json"
        fixture_items = json.loads(fixture_path.read_text(encoding="utf-8"))

        missing_links = [
            item["fields"]["title"]
            for item in fixture_items
            if item["fields"]["is_active"]
            and not (item["fields"]["trailer_url"] or item["fields"]["source_url"])
        ]

        self.assertEqual(missing_links, [])

    def test_demo_fixture_active_homepage_items_include_posters(self):
        fixture_path = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "upcoming_movie_news.json"
        fixture_items = json.loads(fixture_path.read_text(encoding="utf-8"))

        missing_posters = [
            item["fields"]["title"]
            for item in fixture_items
            if item["fields"]["is_active"]
            and not item["fields"]["poster_url"]
        ]

        self.assertEqual(missing_posters, [])

    def test_demo_fixture_does_not_use_known_placeholder_posters(self):
        fixture_path = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "upcoming_movie_news.json"
        fixture_items = json.loads(fixture_path.read_text(encoding="utf-8"))
        placeholder_paths = {"jiangyuan.webp"}

        placeholders = [
            item["fields"]["title"]
            for item in fixture_items
            if item["fields"]["is_active"]
            and any(path in item["fields"]["poster_url"] for path in placeholder_paths)
        ]

        self.assertEqual(placeholders, [])
