from django.test import TestCase
from django.urls import reverse

from apps.movies.models import Movie
from apps.ratings.models import RatingForm, RatingFormMovie, UserRating, UserSession
from apps.recommendations.models import RecommendationResult


class UserFlowTests(TestCase):
    def setUp(self):
        self.form = RatingForm.objects.create(
            category="suspense_crime",
            title="悬疑犯罪电影评分表",
            description="测试评分表",
        )
        self.movies = []
        for index in range(1, 31):
            movie = Movie.objects.create(
                douban_id=f"flow{index}",
                title=f"悬疑电影{index}",
                year=2000 + index,
                directors=[f"导演{index}"],
                actors=[f"演员{index}"],
                genres=["悬疑", "犯罪"],
                countries=["美国"],
                rating=8.0 + (index % 10) / 10,
                rating_count=10000,
                rank=index,
                poster_url="",
                summary="测试电影",
                main_category="suspense_crime",
                feature_tags=["悬疑", "犯罪", "反转"],
            )
            self.movies.append(movie)
            if index <= 12:
                RatingFormMovie.objects.create(form=self.form, movie=movie, sort_order=index)

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "电影资料馆")
        self.assertContains(response, "个性化推荐")

    def test_category_page_lists_five_categories(self):
        response = self.client.get(reverse("ratings:category"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "悬疑犯罪")
        self.assertContains(response, "历史战争传记")

    def test_post_category_creates_session_and_redirects(self):
        response = self.client.post(reverse("ratings:category"), {"category": "suspense_crime"})
        session = UserSession.objects.get()
        self.assertRedirects(response, reverse("ratings:rate", args=[session.session_key]))

    def test_rating_requires_at_least_eight_scores(self):
        session = UserSession.objects.create(selected_category="suspense_crime")
        response = self.client.post(
            reverse("ratings:rate", args=[session.session_key]),
            {f"movie_{self.movies[0].id}": "5"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "请至少评价 8 部电影")

    def test_rating_submission_creates_recommendations(self):
        session = UserSession.objects.create(selected_category="suspense_crime")
        payload = {f"movie_{movie.id}": "5" for movie in self.movies[:8]}

        response = self.client.post(reverse("ratings:rate", args=[session.session_key]), payload)

        self.assertRedirects(response, reverse("ratings:result", args=[session.session_key]))
        self.assertEqual(UserRating.objects.filter(session=session).count(), 8)
        self.assertGreater(RecommendationResult.objects.filter(session=session).count(), 0)

    def test_result_page_loads_saved_recommendations(self):
        session = UserSession.objects.create(selected_category="suspense_crime")
        RecommendationResult.objects.create(
            session=session,
            movie=self.movies[0],
            score=1.0,
            rank_order=1,
            reason="测试推荐理由",
        )

        response = self.client.get(reverse("ratings:result", args=[session.session_key]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "测试推荐理由")
