"""
Scoping: the point of the proposal.

Every alternative to a renderer-driven lookup -- a custom template loader,
``TemplateView``-style specific-to-generic name lists, or dropping
``django/forms/widgets/select.html`` into your own template dir -- resolves on
*global* state. All of them already work today, and none needs a proposal.

They are also all limited to the same thing:

    A global mechanism gives you exactly ONE styling per widget class per
    process. Renderer scoping gives you N.

Admin-vs-frontend is merely the N=2 case that every Django project trips over.
These tests pin N.
"""

import pytest
from django import forms

from tests.conftest import AlphaRenderer
from tests.conftest import BetaRenderer
from tests.conftest import StockRenderer

pytestmark = pytest.mark.django_db


class TestSimultaneousRenderers:
    """One widget class, one process, N different renderings -- at the same time."""

    def test_same_widget_class_renders_differently_per_renderer(self):
        widget = forms.TextInput()

        alpha = widget.render("f", "v", renderer=AlphaRenderer())
        beta = widget.render("f", "v", renderer=BetaRenderer())
        stock = widget.render("f", "v", renderer=StockRenderer())

        assert 'class="alpha-input"' in alpha
        assert 'class="beta-input"' in beta
        assert "alpha-input" not in beta
        assert "beta-input" not in alpha
        # The bare renderer declares nothing, so the widget keeps its own template.
        assert "alpha-input" not in stock
        assert "beta-input" not in stock
        assert 'type="text"' in stock

        # ...and all three are live simultaneously, from one widget instance.
        assert len({alpha, beta, stock}) == 3

    def test_a_single_shared_widget_instance_is_not_mutated(self):
        """Nothing is stashed on the widget: resolution is a pure function of
        (widget class, renderer). Render order cannot leak between renderers."""
        widget = forms.Select(choices=[("a", "A")])

        first = widget.render("f", "a", renderer=AlphaRenderer())
        widget.render("f", "a", renderer=BetaRenderer())
        again = widget.render("f", "a", renderer=AlphaRenderer())

        assert first == again
        assert widget.template_name == forms.Select.template_name

    def test_forms_carry_their_own_renderer(self):
        """The realistic case: two forms, same field types, different styling,
        coexisting in one project."""

        def build(renderer):
            return type(
                "F",
                (forms.Form,),
                {"name": forms.CharField(), "default_renderer": renderer},
            )

        alpha_html = str(build(AlphaRenderer())()["name"])
        beta_html = str(build(BetaRenderer())()["name"])

        assert "alpha-input" in alpha_html
        assert "beta-input" in beta_html

    def test_n_renderers_not_just_two(self):
        """The claim is N, not 2. Build renderers dynamically and prove each
        keeps its own styling with no interference."""
        renderers = [
            type(
                f"R{i}",
                (StockRenderer,),
                {"text_input_template_name": f"{style}/text_input.html"},
            )()
            for i, style in enumerate(["alpha", "beta", "alpha", "beta"])
        ]
        widget = forms.TextInput()
        results = [widget.render("f", "v", renderer=r) for r in renderers]

        assert ["alpha-input" in r for r in results] == [True, False, True, False]
        assert ["beta-input" in r for r in results] == [False, True, False, True]


class TestWhyGlobalIsInsufficient:
    """
    The counter-arguments, made concrete.

    A template loader or a specific-to-generic name list resolves on the
    template engine's global state -- it cannot know *which* renderer asked.
    The best it can do is pick one answer for the whole process.
    """

    def test_widget_class_attribute_is_global_and_wins_everywhere(self):
        """The status quo: monkeypatching ``template_name`` on the class. It
        applies to every consumer at once -- including the admin. There is no
        second answer available."""
        original = forms.Textarea.template_name
        try:
            forms.Textarea.template_name = "alpha/textarea.html"
            widget = forms.Textarea()

            # Every renderer now gets alpha, because the *class* decided.
            assert "alpha-textarea" in widget.render("f", "v", renderer=StockRenderer())
            assert "alpha-textarea" in widget.render("f", "v", renderer=BetaRenderer())
        finally:
            forms.Textarea.template_name = original

    def test_renderer_scoping_can_express_what_global_cannot(self):
        """The same requirement, via the renderer: Beta is unaffected by Alpha."""
        widget = forms.Textarea()
        assert "alpha-textarea" in widget.render("f", "v", renderer=AlphaRenderer())
        # BetaRenderer declares no textarea template -> stock, not alpha.
        assert "alpha-textarea" not in widget.render("f", "v", renderer=BetaRenderer())
