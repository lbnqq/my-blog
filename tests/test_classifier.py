from django.test import SimpleTestCase

from apps.movies.services.classifier import (
    CATEGORY_LABELS,
    classify_main_category,
    normalize_category,
)


class ClassifierTests(SimpleTestCase):
    def test_normalize_category_accepts_known_code(self):
        self.assertEqual(normalize_category("suspense_crime"), "suspense_crime")

    def test_classify_main_category_prefers_suspense_crime(self):
        self.assertEqual(
            classify_main_category(["剧情", "犯罪", "悬疑"]),
            "suspense_crime",
        )

    def test_category_labels_include_five_categories(self):
        self.assertEqual(len(CATEGORY_LABELS), 5)
        self.assertEqual(CATEGORY_LABELS["romance_drama"], "爱情剧情")
