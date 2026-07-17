#!/usr/bin/env python
"""
The proposal in one runnable file.

    pip install django-widget-renderers
    python demo/demo.py

Renders ONE widget class through THREE renderers in ONE process, simultaneously.

No global mechanism -- a custom template loader, a specific-to-generic name list,
or mutating ``Widget.template_name`` -- can produce this output, because each of
them resolves on the template engine's global state and therefore has exactly one
answer to give per process.

That is the argument for https://github.com/django/new-features/issues/172
"""

from pathlib import Path

from django import forms
from django.conf import settings

settings.configure(
    DEBUG=True,
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
        # TemplatesSetting resolves widget templates through the project engine,
        # so Django's own widget templates must be discoverable via APP_DIRS.
        "django.forms",
    ],
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "DIRS": [Path(__file__).parent / "templates"],
        }
    ],
    FORM_RENDERER="django.forms.renderers.TemplatesSetting",
    USE_TZ=True,
)

import django  # noqa: E402

django.setup()

from django.forms.renderers import TemplatesSetting  # noqa: E402

from widget_renderers import install  # noqa: E402

install()


class StockRenderer(TemplatesSetting):
    """Declares nothing -> Django's own markup, untouched."""


class BootstrapishRenderer(TemplatesSetting):
    text_input_template_name = "bootstrapish/text_input.html"


class TailwindishRenderer(TemplatesSetting):
    text_input_template_name = "tailwindish/text_input.html"


def main():
    print(__doc__)
    print("=" * 74)

    widget = forms.TextInput()  # ONE widget instance, never touched

    for renderer in (StockRenderer(), BootstrapishRenderer(), TailwindishRenderer()):
        html = widget.render("email", "you@example.com", renderer=renderer)
        print(f"\n{type(renderer).__name__}:\n  {html.strip()}")

    print("\n" + "=" * 74)
    print("Same widget class. Same instance. Same process. Same moment.")
    print(f"The widget still says: template_name = {widget.template_name!r}")
    print("\nNow the N=2 case every project actually has:")
    print("  a styled site + a stock admin, at once. Global can't express it.")


if __name__ == "__main__":
    main()
