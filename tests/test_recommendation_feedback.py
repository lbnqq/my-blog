from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.movies.models import Movie
from apps.ratings.models import UserSession
from apps.recommendations.models import RecommendationFeedback, RecommendationResult


class RecommendationFeedbackTests(TestCase):
    def setUp(self):
        self.session = UserSession.objects.create(selected_category="suspense_crime")
        self.results = []
        for index in range(1, 22):
            movie = Movie.objects.create(
                douban_id=f"feedback{index}",
                title=f"Feedback Movie {index}",
                year=2000 + index,
                directors=[f"Director {index}"],
                actors=[f"Actor {index}"],
                genres=["Crime", "Drama"],
                countries=["US"],
                rating=8.0,
                rating_count=10000,
                rank=index,
                poster_url="",
                summary="Feedback test movie.",
                main_category="suspense_crime",
                feature_tags=["crime", "drama"],
            )
            self.results.append(
                RecommendationResult.objects.create(
                    session=self.session,
                    movie=movie,
                    score=1.0 - index / 100,
                    rank_order=index,
                    reason=f"Reason {index}",
                    algorithm_version="taskcf_v1",
                )
            )

    def test_result_page_shows_feedback_controls(self):
        response = self.client.get(reverse("ratings:result", args=[self.session.session_key]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'feedback_{self.results[0].id}')
        self.assertContains(response, "推荐反馈")

    def test_guest_can_create_recommendation_feedback(self):
        response = self.client.post(
            reverse("ratings:result", args=[self.session.session_key]),
            {f"feedback_{self.results[0].id}": "5"},
        )

        self.assertRedirects(response, reverse("ratings:result", args=[self.session.session_key]))
        feedback = RecommendationFeedback.objects.get(recommendation_result=self.results[0])
        self.assertEqual(feedback.rating, 5)

    def test_feedback_update_reuses_existing_row_and_blanks_do_not_delete(self):
        RecommendationFeedback.objects.create(recommendation_result=self.results[0], rating=4)

        self.client.post(
            reverse("ratings:result", args=[self.session.session_key]),
            {
                f"feedback_{self.results[0].id}": "2",
                f"feedback_{self.results[1].id}": "",
            },
        )

        self.assertEqual(RecommendationFeedback.objects.count(), 1)
        feedback = RecommendationFeedback.objects.get(recommendation_result=self.results[0])
        self.assertEqual(feedback.rating, 2)

    def test_logged_in_feedback_can_be_traced_to_session_user(self):
        user = get_user_model().objects.create_user(username="alice", password="secret12345")
        self.session.user = user
        self.session.save(update_fields=["user"])
        self.client.force_login(user)

        self.client.post(
            reverse("ratings:result", args=[self.session.session_key]),
            {f"feedback_{self.results[0].id}": "5"},
        )

        feedback = RecommendationFeedback.objects.get(recommendation_result=self.results[0])
        self.assertEqual(feedback.recommendation_result.session.user, user)

    def test_logged_in_history_detail_allows_feedback(self):
        user = get_user_model().objects.create_user(username="alice", password="secret12345")
        self.session.user = user
        self.session.save(update_fields=["user"])
        self.client.force_login(user)
        detail_url = reverse(
            "accounts:recommendation_history_detail",
            args=[self.session.session_key],
        )

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'feedback_{self.results[0].id}')
        self.assertContains(response, "推荐反馈")

        post_response = self.client.post(detail_url, {f"feedback_{self.results[0].id}": "4"})

        self.assertRedirects(post_response, detail_url)
        feedback = RecommendationFeedback.objects.get(recommendation_result=self.results[0])
        self.assertEqual(feedback.rating, 4)


class RecommendationAnalyticsTests(TestCase):
    def setUp(self):
        self.session = UserSession.objects.create(selected_category="suspense_crime")
        self.results = []
        for index in range(1, 7):
            movie = Movie.objects.create(
                douban_id=f"analytics{index}",
                title=f"Analytics Movie {index}",
                year=2000 + index,
                directors=[f"Director {index}"],
                actors=[f"Actor {index}"],
                genres=["Crime"],
                countries=["US"],
                rating=8.0,
                rating_count=10000,
                rank=index,
                poster_url="",
                summary="Analytics test movie.",
                main_category="suspense_crime",
                feature_tags=["crime"],
            )
            self.results.append(
                RecommendationResult.objects.create(
                    session=self.session,
                    movie=movie,
                    score=1.0,
                    rank_order=index,
                    reason=f"Reason {index}",
                    algorithm_version="taskcf_v1" if index < 6 else "taskcf_v2",
                )
            )
        RecommendationFeedback.objects.create(recommendation_result=self.results[0], rating=5)
        RecommendationFeedback.objects.create(recommendation_result=self.results[1], rating=4)
        RecommendationFeedback.objects.create(recommendation_result=self.results[4], rating=2)
        RecommendationFeedback.objects.create(recommendation_result=self.results[5], rating=1)

    def test_analytics_requires_login(self):
        response = self.client.get(reverse("recommendations:analytics"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('recommendations:analytics')}",
        )

    def test_analytics_rejects_non_staff_user(self):
        user = get_user_model().objects.create_user(username="alice", password="secret12345")
        self.client.force_login(user)

        response = self.client.get(reverse("recommendations:analytics"))

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_view_analytics_metrics(self):
        staff = get_user_model().objects.create_user(
            username="staff", password="secret12345", is_staff=True
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("recommendations:analytics"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "推荐结果总数")
        self.assertContains(response, "6")
        self.assertContains(response, "反馈覆盖率")
        self.assertContains(response, "66.7%")
        self.assertContains(response, "平均反馈分")
        self.assertContains(response, "3.00")
        self.assertContains(response, "好评率")
        self.assertContains(response, "50.0%")
        self.assertContains(response, "Top1")
        self.assertContains(response, "Top2-5")
        self.assertContains(response, "taskcf_v1")
        self.assertContains(response, "taskcf_v2")


class RecommendationFeedbackAdminTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(
            username="staff",
            email="staff@example.com",
            password="secret12345",
        )
        self.user = get_user_model().objects.create_user(username="alice", password="secret12345")
        self.session = UserSession.objects.create(selected_category="suspense_crime", user=self.user)
        movie = Movie.objects.create(
            douban_id="admin-feedback",
            title="Admin Feedback Movie",
            year=2024,
            directors=["Director"],
            actors=["Actor"],
            genres=["Crime"],
            countries=["US"],
            rating=8.0,
            rating_count=10000,
            rank=1,
            poster_url="",
            summary="Admin feedback test movie.",
            main_category="suspense_crime",
            feature_tags=["crime"],
        )
        self.result = RecommendationResult.objects.create(
            session=self.session,
            movie=movie,
            score=0.98,
            rank_order=3,
            reason="Admin reason",
            algorithm_version="taskcf_v1",
        )
        RecommendationFeedback.objects.create(recommendation_result=self.result, rating=5)
        self.client.force_login(self.staff)

    def test_feedback_admin_changelist_shows_user_category_movie_and_algorithm_context(self):
        response = self.client.get(
            reverse("admin:recommendation_feedback_user", args=["suspense_crime", self.user.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice")
        self.assertContains(response, "悬疑犯罪")
        self.assertContains(response, "Admin Feedback Movie")
        self.assertContains(response, "#03")
        self.assertContains(response, "taskcf_v1")
        self.assertContains(response, "5")

    def test_feedback_admin_uses_three_level_category_user_feedback_directory(self):
        cykg = get_user_model().objects.create_user(username="cykg", password="secret12345")
        comedy_session = UserSession.objects.create(selected_category="comedy_animation", user=cykg)
        comedy_movie = Movie.objects.create(
            douban_id="cykg-comedy",
            title="Comedy Feedback Movie",
            year=2025,
            directors=["Director"],
            actors=["Actor"],
            genres=["Comedy"],
            countries=["US"],
            rating=8.0,
            rating_count=10000,
            rank=2,
            poster_url="",
            summary="Comedy feedback test movie.",
            main_category="comedy_animation",
            feature_tags=["comedy"],
        )
        comedy_result = RecommendationResult.objects.create(
            session=comedy_session,
            movie=comedy_movie,
            score=0.88,
            rank_order=1,
            reason="Comedy reason",
            algorithm_version="taskcf_v1",
        )
        RecommendationFeedback.objects.create(recommendation_result=comedy_result, rating=4)

        category_response = self.client.get(reverse("admin:recommendations_recommendationfeedback_changelist"))
        users_response = self.client.get(
            reverse("admin:recommendation_feedback_category", args=["comedy_animation"])
        )
        user_feedback_response = self.client.get(
            reverse("admin:recommendation_feedback_user", args=["comedy_animation", cykg.id])
        )

        self.assertEqual(category_response.status_code, 200)
        self.assertContains(category_response, "悬疑犯罪")
        self.assertContains(category_response, "爱情剧情")
        self.assertContains(category_response, "喜剧动画")
        self.assertContains(category_response, "科幻动作冒险")
        self.assertContains(category_response, "历史战争传记")
        self.assertContains(category_response, reverse("admin:recommendation_feedback_category", args=["comedy_animation"]))

        self.assertEqual(users_response.status_code, 200)
        self.assertContains(users_response, "喜剧动画")
        self.assertContains(users_response, "cykg", count=1)
        self.assertContains(users_response, reverse("admin:recommendation_feedback_user", args=["comedy_animation", cykg.id]))

        self.assertEqual(user_feedback_response.status_code, 200)
        self.assertContains(user_feedback_response, "cykg")
        self.assertContains(user_feedback_response, "喜剧动画")
        self.assertContains(user_feedback_response, "Comedy Feedback Movie")
        self.assertContains(user_feedback_response, "#01")
        self.assertContains(user_feedback_response, "4")
