from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.movies.models import Movie
from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie
from apps.ratings.models import RatingForm, RatingFormMovie, UserSession
from apps.recommendations.models import RecommendationResult


class FrontendRedesignTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.movies = [
            Movie.objects.create(
                douban_id=f"redesign-{index}",
                title=f"Redesign Movie {index}",
                year=2000 + index,
                rating=8.0,
                rank=index,
                genres=["剧情"],
                main_category="suspense_crime",
                summary="用于新版前端模板测试。",
            )
            for index in range(1, 10)
        ]
        rating_form = RatingForm.objects.create(
            category="suspense_crime",
            title="悬疑犯罪评分表",
            is_active=True,
        )
        RatingFormMovie.objects.bulk_create(
            [
                RatingFormMovie(form=rating_form, movie=movie, sort_order=index)
                for index, movie in enumerate(cls.movies)
            ]
        )

    def test_base_uses_editorial_navigation_and_frontend_script(self):
        response = self.client.get(reverse("ratings:category"))

        self.assertContains(response, 'class="navbar"')
        self.assertContains(response, 'class="navbar__hamburger"')
        self.assertContains(response, "css/site.css")
        self.assertContains(response, "js/site.js")

    def test_category_page_keeps_real_django_values_in_new_cards(self):
        response = self.client.get(reverse("ratings:category"))

        self.assertContains(response, 'class="category-card"')
        self.assertContains(response, 'value="suspense_crime"')
        self.assertContains(response, 'value="history_war_biography"')

    def test_rating_page_uses_accessible_star_radios_and_progress_contract(self):
        session = UserSession.objects.create(selected_category="suspense_crime")
        response = self.client.get(reverse("ratings:rate", args=[session.session_key]))

        self.assertContains(response, 'class="star-input"')
        self.assertContains(response, f'name="movie_{self.movies[0].id}"')
        self.assertContains(response, 'data-rating-form')
        self.assertContains(response, 'data-rated-count')

    def test_result_page_uses_feedback_stars_without_changing_field_names(self):
        session = UserSession.objects.create(selected_category="suspense_crime")
        result = RecommendationResult.objects.create(
            session=session,
            movie=self.movies[0],
            score=0.9,
            rank_order=1,
            reason="测试推荐理由",
        )
        response = self.client.get(reverse("ratings:result", args=[session.session_key]))

        self.assertContains(response, 'class="result-card"')
        self.assertContains(response, f'name="feedback_{result.id}"')
        self.assertContains(response, 'class="star-input star-input--compact"')

    def test_authenticated_navigation_shows_history_and_logout(self):
        user = get_user_model().objects.create_user(username="redesign-user", password="secret12345")
        self.client.force_login(user)

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, reverse("accounts:recommendation_history"))
        self.assertContains(response, reverse("accounts:logout"))
        self.assertNotContains(response, reverse("accounts:register"))

    def test_analytics_has_responsive_table_wrapper(self):
        staff = get_user_model().objects.create_user(
            username="redesign-staff",
            password="secret12345",
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("recommendations:analytics"))

        self.assertContains(response, 'class="table-scroll"')
        self.assertContains(response, 'class="analytics-grid"')

    def test_homepage_keeps_fallback_beneath_remote_chart_posters(self):
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="weekly-fallback",
            rank=1,
            title="Weekly Fallback Movie",
            poster_url="https://example.com/weekly.jpg",
            subject_url="https://example.com/weekly",
            fetched_at=timezone.now(),
            is_active=True,
        )
        DoubanChartMovie.objects.create(
            douban_id="chart-fallback",
            rank=1,
            title="Chart Fallback Movie",
            poster_url="https://example.com/chart.jpg",
            subject_url="https://example.com/chart",
            fetched_at=timezone.now(),
            is_active=True,
        )

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, '<span class="poster-fallback movie-card__fallback">Weekly Fallback Movie</span>')
        self.assertContains(response, '<span class="poster-fallback movie-card__fallback">Chart Fallback Movie</span>')
        self.assertContains(response, 'onerror="this.style.display=\'none\'"', count=2)
