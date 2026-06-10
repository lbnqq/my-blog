from django.utils.functional import lazy
from django.utils.translation import get_language


def bilingual_label(chinese, english):
    def translate_label():
        language = get_language() or ""
        return english if language.startswith("en") else chinese

    return lazy(translate_label, str)()
