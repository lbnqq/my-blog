from django import forms

from apps.movies.services.classifier import CATEGORY_LABELS


class CategorySelectionForm(forms.Form):
    category = forms.ChoiceField(
        choices=[(code, label) for code, label in CATEGORY_LABELS.items()],
        widget=forms.RadioSelect,
    )
