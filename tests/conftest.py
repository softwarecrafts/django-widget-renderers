"""Shared fixtures: renderers and widgets used across the suite."""

from django import forms
from django.forms.renderers import TemplatesSetting


class AlphaRenderer(TemplatesSetting):
    """A styled renderer."""

    text_input_template_name = "alpha/text_input.html"
    select_template_name = "alpha/select.html"
    textarea_template_name = "alpha/textarea.html"


class BetaRenderer(TemplatesSetting):
    """A second, independent styled renderer -- different templates, same widgets."""

    text_input_template_name = "beta/text_input.html"
    select_template_name = "beta/select.html"


class StockRenderer(TemplatesSetting):
    """Declares nothing, so every widget keeps its own template."""


class MoneyInput(forms.TextInput):
    """A custom widget with its own template (the shadowing case)."""

    template_name = "custom_money.html"


class StubRenderer:
    """A renderer is any object; lookup is just getattr."""

    def __init__(self, **template_names):
        self.__dict__.update(template_names)
