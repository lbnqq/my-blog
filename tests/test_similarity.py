from django.test import SimpleTestCase

from apps.recommendations.services.similarity import (
    jaccard_similarity,
    normalize_douban_rating,
    normalize_rank,
)


class SimilarityTests(SimpleTestCase):
    def test_jaccard_similarity_scores_overlap(self):
        self.assertEqual(
            jaccard_similarity(["悬疑", "犯罪"], ["犯罪", "剧情"]),
            1 / 3,
        )

    def test_normalize_douban_rating_bounds_value(self):
        self.assertEqual(normalize_douban_rating(9.8), 1.0)
        self.assertEqual(normalize_douban_rating(7.0), 0.0)

    def test_normalize_rank_prefers_smaller_rank(self):
        self.assertGreater(normalize_rank(1), normalize_rank(1000))
