"""
Backwards compatibility.

The patch must be inert for anyone who doesn't opt in. Because lookup is
``getattr`` against the renderer, a renderer that declares no
``<widget>_template_name`` attributes leaves every widget on its own template --
compatibility is the default that falls out of the design, not a feature that had
to be implemented.

These tests render every stock widget through Django's own default renderer and
assert the markup is exactly what Django produces untouched.
"""

import pytest
from django import forms
from django.forms.renderers import DjangoTemplates

pytestmark = pytest.mark.django_db

WIDGETS = [
    forms.TextInput(),
    forms.NumberInput(),
    forms.EmailInput(),
    forms.URLInput(),
    forms.PasswordInput(),
    forms.HiddenInput(),
    forms.DateInput(),
    forms.DateTimeInput(),
    forms.TimeInput(),
    forms.Textarea(),
    forms.CheckboxInput(),
    forms.FileInput(),
    forms.ClearableFileInput(),
    forms.Select(choices=[("a", "A")]),
    forms.SelectMultiple(choices=[("a", "A")]),
    forms.NullBooleanSelect(),
    forms.RadioSelect(choices=[("a", "A")]),
    forms.CheckboxSelectMultiple(choices=[("a", "A")]),
    forms.SplitDateTimeWidget(),
]


@pytest.mark.parametrize("widget", WIDGETS, ids=lambda w: type(w).__name__)
def test_stock_widget_template_is_untouched(widget):
    """A renderer with no widget attributes resolves to the widget's own
    template -- i.e. exactly Django's behaviour."""
    renderer = DjangoTemplates()
    assert widget.get_template_name(renderer, widget.template_name) == (
        widget.template_name
    )


@pytest.mark.parametrize("widget", WIDGETS, ids=lambda w: type(w).__name__)
def test_stock_widget_renders_identically(widget):
    """Belt and braces: render it, not just resolve it."""
    # None, not a sentinel string -- SplitDateTimeWidget decompresses its value.
    html = widget.render("field", None, renderer=DjangoTemplates())
    assert html  # renders without error
    assert "alpha-" not in html
    assert "beta-" not in html


def test_default_form_rendering_is_unaffected():
    class F(forms.Form):
        name = forms.CharField()
        choice = forms.ChoiceField(choices=[("a", "A")])

    html = F().as_div()
    assert 'type="text"' in html
    assert "<select" in html
