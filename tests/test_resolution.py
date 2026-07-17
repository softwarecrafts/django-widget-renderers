"""
The resolution rules, tested directly against the hook.

No templates, no rendering -- this is the API proposed in
https://github.com/django/new-features/issues/172:
``Widget.get_template_name(renderer, template_name)``.
"""

from django import forms

from tests.conftest import MoneyInput
from tests.conftest import StubRenderer
from widget_renderers import widget_slug

STOCK = "django/forms/widgets/stock.html"  # stand-in for a widget's own template


class TestWidgetSlug:
    def test_single_word(self):
        assert widget_slug(forms.Select) == "select"

    def test_camel_case_becomes_snake_case(self):
        assert widget_slug(forms.TextInput) == "text_input"
        assert widget_slug(forms.RadioSelect) == "radio_select"
        assert widget_slug(forms.CheckboxSelectMultiple) == "checkbox_select_multiple"


class TestGetTemplateName:
    def test_exact_class_match(self):
        renderer = StubRenderer(select_template_name="alpha/select.html")
        assert forms.Select().get_template_name(renderer, STOCK) == "alpha/select.html"

    def test_lookup_uses_snake_case(self):
        """Matches Django's existing ``form_template_name`` convention."""
        renderer = StubRenderer(radio_select_template_name="alpha/radio.html")
        assert (
            forms.RadioSelect().get_template_name(renderer, STOCK) == "alpha/radio.html"
        )

    def test_unstyled_subclass_resolves_up_the_mro(self):
        """``SelectMultiple`` declares no ``template_name`` -- it inherits
        ``Select``'s -- so it must pick up ``select_template_name`` too.

        Resolving only on ``self.__class__.__name__`` (as the issue's sketch
        does) would silently render ``SelectMultiple`` stock while ``Select``
        renders styled.
        """
        renderer = StubRenderer(select_template_name="alpha/select.html")
        assert (
            forms.SelectMultiple().get_template_name(renderer, STOCK)
            == "alpha/select.html"
        )
        assert (
            forms.NullBooleanSelect().get_template_name(renderer, STOCK)
            == "alpha/select.html"
        )

    def test_own_template_name_shadows_a_base_override(self):
        """``MoneyInput(TextInput)`` defines its own template, so a renderer's
        ``text_input_template_name`` must not clobber it."""
        renderer = StubRenderer(text_input_template_name="alpha/text_input.html")
        assert MoneyInput().get_template_name(renderer, STOCK) == STOCK

    def test_custom_widget_can_still_be_targeted_explicitly(self):
        """Shadowing is not a lockout: name the widget and the renderer wins."""
        renderer = StubRenderer(money_input_template_name="alpha/money.html")
        assert MoneyInput().get_template_name(renderer, STOCK) == "alpha/money.html"

    def test_bare_renderer_returns_the_widget_template_unchanged(self):
        """Backwards compatibility isn't a feature -- it's the default. A
        renderer declaring nothing leaves every widget on its own template."""
        renderer = StubRenderer()
        for widget in (forms.Select(), forms.TextInput(), MoneyInput()):
            assert widget.get_template_name(renderer, STOCK) == STOCK

    def test_hook_is_overridable(self):
        """The hook is the extension point: override it to change or trace
        resolution (answers 'renderer-driven templates make debugging harder')."""

        class TracingInput(forms.TextInput):
            def get_template_name(self, renderer, template_name):
                resolved = super().get_template_name(renderer, template_name)
                self.trace = (template_name, resolved)
                return "override.html"

        widget = TracingInput()
        renderer = StubRenderer(text_input_template_name="alpha/text_input.html")
        assert widget.get_template_name(renderer, STOCK) == "override.html"
        assert widget.trace == (STOCK, "alpha/text_input.html")

    def test_lookup_key_never_comes_from_instance_or_user_data(self):
        """The renderer attribute is derived purely from the widget's *class*
        name -- never from attrs, instance state, or submitted data. Nothing
        user-controlled can steer the template (answers the injection-vector
        concern raised on the proposal)."""
        widget = forms.Select(attrs={"template_name": "attacker.html"})
        widget.evil = "attacker.html"

        renderer = StubRenderer(select_template_name="alpha/select.html")
        assert widget.get_template_name(renderer, STOCK) == "alpha/select.html"

        # ...and with nothing declared it can't be steered anywhere either.
        assert widget.get_template_name(StubRenderer(), STOCK) == STOCK
