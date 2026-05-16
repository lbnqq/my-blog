from django.test import SimpleTestCase

from apps.recommendations.services.parameter_selector import choose_parameter_group


class ParameterSelectorTests(SimpleTestCase):
    def test_choose_parameter_group_uses_type_first_for_few_ratings(self):
        params = choose_parameter_group([5, 4, 3, 4, 5, 3, 4, 5])
        self.assertEqual(params.name, "type_first")

    def test_choose_parameter_group_uses_similarity_first_for_clear_preferences(self):
        params = choose_parameter_group([5, 1, 5, 1, 4, 2, 5, 1, 4, 2, 5, 1])
        self.assertEqual(params.name, "similarity_first")

    def test_choose_parameter_group_uses_quality_first_for_flat_ratings(self):
        params = choose_parameter_group([3, 3, 3, 4, 3, 3, 3, 3, 4, 3, 3, 3])
        self.assertEqual(params.name, "quality_first")
