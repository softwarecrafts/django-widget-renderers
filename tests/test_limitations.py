"""
Known limitations, pinned as tests.

These are real gaps, documented on purpose. Better to state them plainly than to
have them discovered during review.
"""

import pytest
from django import forms
from django.forms.renderers import get_default_renderer

from tests.conftest import AlphaRenderer

pytestmark = pytest.mark.django_db


def test_multiwidget_subwidgets_are_not_reached():
    """A ``MultiWidget`` renders its subwidgets from *its own* context, not via
    their ``render()``, so the hook never sees them.

    ``SplitDateTimeWidget`` is two ``DateInput``/``TimeInput``s -- styling
    ``text_input_template_name`` does not reach them. To style subwidgets, set
    their ``template_name`` directly or give the MultiWidget a template that
    names the subwidget templates it wants.
    """
    widget = forms.SplitDateTimeWidget()
    html = widget.render("dt", None, renderer=AlphaRenderer())

    # The parent resolves fine; the children do not consult the renderer.
    assert "alpha-input" not in html


def test_widgets_rendered_without_a_renderer_fall_back_to_the_global_default():
    """``Widget.render()`` with no renderer uses ``get_default_renderer()``, so
    renderer scoping cannot reach code that never passes one.

    This is not hypothetical: ``ModelAdmin.action_checkbox`` renders
    ``CheckboxInput(attrs={"class": "action-select"})`` with no renderer, so
    inside the admin it picks up the *project* default. If that template drops
    the caller's ``class``, ``actions.js`` never wires ``#action-toggle`` and the
    changelist "select all" silently stops working.

    Scoping helps forms. It cannot help widgets rendered outside one.
    """
    assert (
        forms.TextInput().get_template_name(
            get_default_renderer(), forms.TextInput.template_name
        )
        == forms.TextInput.template_name
    )  # FORM_RENDERER declares nothing here

    # ...but whatever FORM_RENDERER is, that is what such call sites get.
    html = forms.TextInput().render("f", "v")
    assert "alpha-input" not in html
