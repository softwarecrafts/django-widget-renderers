"""
The proposal, as a monkeypatch.

``install()`` adds a ``Widget.get_template_name`` hook and wires it into
``Widget._render``, so a widget's template comes from the active renderer instead
of the widget class.

Everything here exists only because we cannot edit Django from out-of-tree.
In-tree, the change would be exactly this -- a method, plus one line in
``_render``. See PROPOSAL.md.
"""

import re

from django.forms.renderers import get_default_renderer
from django.forms.widgets import Widget
from django.utils.safestring import mark_safe

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")
_state = {"installed": False}


def widget_slug(widget_class):
    """``TextInput`` -> ``text_input``. The renderer attribute stem."""
    return _CAMEL_BOUNDARY.sub("_", widget_class.__name__).lower()


def install():
    """Apply the patch. Idempotent -- safe to call more than once."""
    if _state["installed"]:
        return

    def get_template_name(self, renderer, template_name):
        """
        Return the template ``renderer`` wants for this widget.

        Walks the widget MRO looking for a ``<widget>_template_name`` on the
        renderer. A class that defines its own ``template_name`` short-circuits
        the walk (attribute shadowing): a custom widget keeps its own template
        over a base override, while an unstyled subclass resolves *up* to a
        styled base -- ``SelectMultiple`` picks up ``select_template_name``.

        Falls back to ``template_name`` (the widget's own), so a renderer that
        declares nothing renders stock markup unchanged.
        """
        for klass in type(self).__mro__:
            override = getattr(renderer, f"{widget_slug(klass)}_template_name", None)
            if override is not None:
                return override
            if "template_name" in klass.__dict__:
                break
        return template_name

    def _render(self, template_name, context, renderer=None):
        if renderer is None:
            renderer = get_default_renderer()
        template_name = self.get_template_name(renderer, template_name)
        # Same trust posture as Django's own Widget._render.
        return mark_safe(renderer.render(template_name, context))  # noqa: S308

    Widget.get_template_name = get_template_name
    Widget._render = _render  # noqa: SLF001
    _state["installed"] = True
