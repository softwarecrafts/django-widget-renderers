"""
Optional convenience AppConfig.

Add ``"widget_renderers"`` to ``INSTALLED_APPS`` to install the patch
automatically at startup. Projects that would rather control ordering (e.g.
define their renderers first) can skip this and call ``install()`` from their own
``AppConfig.ready()`` instead.
"""

from django.apps import AppConfig


class WidgetRenderersConfig(AppConfig):
    name = "widget_renderers"
    verbose_name = "Widget renderers"

    def ready(self):
        from .patches import install

        install()
