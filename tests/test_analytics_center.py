from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie, UpcomingMovieNews
from apps.movies.models import Movie
from apps.ratings.models import UserRating, UserSession
from apps.recommendations.models import RecommendationFeedback, RecommendationResult, SyncRun


class AnalyticsCenterTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="analyst", password="secret12345", is_staff=True
        )
        self.user = get_user_model().objects.create_user(
            username="viewer", password="secret12345"
        )
        self.movie = Movie.objects.create(
            douban_id="analytics-center-1",
            title="真实统计电影",
            year=2024,
            directors=["测试导演"],
            actors=["测试演员"],
            genres=["悬疑", "犯罪"],
            countries=["中国"],
            rating=8.5,
            rating_count=12345,
            rank=1,
            poster_url="",
            summary="用于统计中心测试。",
            main_category="suspense_crime",
            feature_tags=["悬疑"],
        )
        self.session = UserSession.objects.create(
            selected_category="suspense_crime", user=self.user, completed_at=timezone.now()
        )
        UserRating.objects.create(session=self.session, movie=self.movie, rating=5)
        self.result = RecommendationResult.objects.create(
            session=self.session,
            movie=self.movie,
            score=0.91,
            rank_order=1,
            reason="真实统计推荐理由",
            algorithm_version="taskcf_v1",
        )
        RecommendationFeedback.objects.create(recommendation_result=self.result, rating=5)

    def test_all_analytics_pages_require_staff(self):
        names = [
            "recommendations:center",
            "recommendations:analytics",
            "recommendations:user_analytics",
            "recommendations:movie_analytics",
            "recommendations:data_quality",
        ]
        for name in names:
            url = reverse(name)
            anonymous = self.client.get(url)
            self.assertRedirects(anonymous, f"{reverse('accounts:login')}?next={url}")

            self.client.force_login(self.user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.logout()

            self.client.force_login(self.staff)
            self.assertEqual(self.client.get(url).status_code, 200)
            self.client.logout()

    def test_center_links_four_real_analytics_pages_and_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("recommendations:center"))

        self.assertContains(response, reverse("recommendations:analytics"))
        self.assertContains(response, reverse("recommendations:user_analytics"))
        self.assertContains(response, reverse("recommendations:movie_analytics"))
        self.assertContains(response, reverse("recommendations:data_quality"))
        self.assertContains(response, reverse("admin:index"))

    def test_recommendation_filters_exclude_out_of_range_sessions(self):
        old_session = UserSession.objects.create(selected_category="romance_drama")
        UserSession.objects.filter(pk=old_session.pk).update(
            created_at=timezone.now() - timedelta(days=40)
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("recommendations:analytics"),
            {"period": "7d", "category": "suspense_crime", "version": "taskcf_v1"},
        )

        self.assertEqual(response.context["metrics"]["session_count"], 1)
        self.assertEqual(response.context["metrics"]["result_count"], 1)
        self.assertEqual(response.context["metrics"]["feedback_count"], 1)
        self.assertContains(response, "真实统计电影")

    def test_user_analytics_treats_guest_sessions_separately(self):
        UserSession.objects.create(selected_category="suspense_crime")
        UserSession.objects.create(selected_category="suspense_crime")
        self.client.force_login(self.staff)

        response = self.client.get(reverse("recommendations:user_analytics"))

        self.assertEqual(response.context["metrics"]["guest_session_count"], 2)
        self.assertEqual(response.context["metrics"]["authenticated_session_count"], 1)

    def test_user_analytics_new_users_respects_custom_end_date(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("recommendations:user_analytics"),
            {
                "period": "custom",
                "date_from": "2020-01-01",
                "date_to": "2020-01-31",
            },
        )

        self.assertEqual(response.context["metrics"]["new_user_count"], 0)

    def test_user_retention_excludes_users_without_a_full_observation_window(self):
        now = timezone.now()
        retained_user = get_user_model().objects.create_user(
            username="retained", password="secret12345"
        )
        recent_user = get_user_model().objects.create_user(
            username="recent", password="secret12345"
        )
        UserSession.objects.create(
            selected_category="suspense_crime",
            user=retained_user,
            completed_at=now - timedelta(days=10),
        )
        UserSession.objects.create(
            selected_category="suspense_crime",
            user=retained_user,
            completed_at=now - timedelta(days=5),
        )
        UserSession.objects.create(
            selected_category="suspense_crime",
            user=recent_user,
            completed_at=now - timedelta(days=2),
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("recommendations:user_analytics"), {"period": "all"}
        )

        self.assertEqual(response.context["retention"]["seven_day"], 100)
        self.assertEqual(response.context["retention"]["thirty_day"], 0)

    def test_movie_analytics_uses_real_feedback_and_pagination(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("recommendations:movie_analytics"),
            {"category": "suspense_crime", "sort": "average_rating"},
        )

        row = response.context["movie_page"].object_list[0]
        self.assertEqual(row.title, "真实统计电影")
        self.assertEqual(row.recommendation_count, 1)
        self.assertEqual(row.feedback_count, 1)
        self.assertEqual(row.average_feedback, 5)
        self.assertContains(response, "真实统计电影")

    def test_movie_analytics_sorts_coverage_by_ratio_not_feedback_count(self):
        lower_coverage = Movie.objects.create(
            douban_id="analytics-center-coverage",
            title="More feedback lower coverage",
            year=2024,
            rating=8.0,
            rank=2,
            main_category="suspense_crime",
        )
        for index in range(3):
            session = UserSession.objects.create(
                selected_category="suspense_crime", completed_at=timezone.now()
            )
            result = RecommendationResult.objects.create(
                session=session,
                movie=lower_coverage,
                score=0.8,
                rank_order=1,
                reason="coverage test",
            )
            if index < 2:
                RecommendationFeedback.objects.create(
                    recommendation_result=result, rating=4
                )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("recommendations:movie_analytics"),
            {"category": "suspense_crime", "sort": "coverage"},
        )

        rows = list(response.context["movie_page"].object_list)
        self.assertEqual(rows[0].pk, self.movie.pk)
        self.assertEqual(rows[0].coverage_rate, 100)

    def test_data_quality_uses_real_missing_field_counts(self):
        Movie.objects.create(
            title="缺失数据电影",
            rating=6.0,
            main_category="romance_drama",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("recommendations:data_quality"))

        self.assertEqual(response.context["quality"]["missing_poster"], 2)
        self.assertEqual(response.context["quality"]["missing_summary"], 1)
        self.assertEqual(response.context["quality"]["missing_douban_id"], 1)

    def test_analytics_charts_expose_pointer_tooltips(self):
        script = Path("static/js/analytics.js").read_text(encoding="utf-8")

        self.assertIn('addEventListener("pointermove"', script)
        self.assertIn('addEventListener("pointerleave"', script)
        self.assertIn("_chartHits", script)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("recommendations:movie_analytics"))
        self.assertContains(response, "analytics.js?v=20260614")


class AnalyticsSyncTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="sync-admin", password="secret12345", is_staff=True
        )
        self.user = get_user_model().objects.create_user(
            username="sync-viewer", password="secret12345"
        )

    def test_sync_endpoint_is_post_only_and_staff_only(self):
        url = reverse("recommendations:sync_data", args=["douban_chart"])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 405)

        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url).status_code, 403)

    @patch("apps.recommendations.views.sync_douban_chart")
    def test_chart_sync_creates_success_log(self, sync_chart):
        sync_chart.return_value.status = "updated"
        sync_chart.return_value.updated_count = 10
        sync_chart.return_value.message = "Updated 10 movies."
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("recommendations:sync_data", args=["douban_chart"])
        )

        self.assertRedirects(response, reverse("recommendations:data_quality"))
        sync_chart.assert_called_once_with(force=True)
        run = SyncRun.objects.get()
        self.assertEqual(run.source, SyncRun.Source.DOUBAN_CHART)
        self.assertEqual(run.status, SyncRun.Status.SUCCESS)
        self.assertEqual(run.updated_count, 10)
        self.assertEqual(run.triggered_by, self.staff)
        self.assertIsNotNone(run.finished_at)

    @patch("apps.recommendations.views.sync_douban_weekly_reputation")
    def test_failed_sync_is_logged(self, sync_weekly):
        sync_weekly.return_value.status = "failed"
        sync_weekly.return_value.updated_count = 0
        sync_weekly.return_value.message = "Network timeout"
        self.client.force_login(self.staff)

        self.client.post(
            reverse("recommendations:sync_data", args=["weekly_reputation"])
        )

        run = SyncRun.objects.get()
        self.assertEqual(run.status, SyncRun.Status.FAILED)
        self.assertIn("Network timeout", run.message)

    @patch("apps.recommendations.views.sync_douban_weekly_reputation")
    @patch("apps.recommendations.views.sync_douban_chart")
    def test_sync_all_runs_both_sources(self, sync_chart, sync_weekly):
        for mock, count in ((sync_chart, 10), (sync_weekly, 6)):
            mock.return_value.status = "updated"
            mock.return_value.updated_count = count
            mock.return_value.message = "ok"
        self.client.force_login(self.staff)

        self.client.post(reverse("recommendations:sync_all"))

        self.assertEqual(SyncRun.objects.count(), 2)
        self.assertEqual(
            list(SyncRun.objects.order_by("started_at").values_list("source", flat=True)),
            [SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION],
        )
