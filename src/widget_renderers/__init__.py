"""
Renderer-driven widget templates for Django forms.

Reference implementation of https://github.com/django/new-features/issues/172.

    from widget_renderers import install

    class MyAppConfig(AppConfig):
        def ready(self):
            install()

A renderer then declares a template per widget, using the same
``<widget>_template_name`` convention Django already uses for
``form_template_name`` / ``field_template_name``::

    class DrawerRenderer(TemplatesSetting):
        text_input_template_name = "forms/drawer.html#text_input"
        select_template_name = "forms/drawer.html#select"
"""

from .admin import RendererAdminMixin
from .admin import RendererAdminSite
from .admin import with_renderer
from .patches import install
from .patches import widget_slug

__all__ = [
    "RendererAdminMixin",
    "RendererAdminSite",
    "install",
    "widget_slug",
    "with_renderer",
]
