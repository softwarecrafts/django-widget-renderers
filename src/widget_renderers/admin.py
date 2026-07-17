"""
Admin integration -- scaffolding, not part of the proposal.

An admin site declares which renderer its forms use, and that renderer is
injected as each form's ``default_renderer``, which takes precedence over the
global ``FORM_RENDERER``.

For a stock-widget admin, point ``form_renderer`` at a renderer that declares no
``<widget>_template_name`` attributes (e.g. Django's plain ``TemplatesSetting``):
its forms then render Django's stock widget markup, which the admin's JS-driven
widgets depend on.

In-tree, none of this would be needed -- ``django.contrib.admin`` would simply
declare its renderer. See PROPOSAL.md.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin import ModelAdmin


class RendererAdminMixin:
    """
    Mix into a ModelAdmin/InlineModelAdmin to set ``form_renderer`` as the
    ``default_renderer`` on the forms/formsets it builds.
    """

    # A renderer instance or class. ``None`` leaves forms on the project default.
    form_renderer = None

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if self.form_renderer is not None:
            form.default_renderer = self.form_renderer
        return form

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if self.form_renderer is not None:
            formset.form.default_renderer = self.form_renderer
        return formset


def with_renderer(admin_class, renderer):
    """
    Return an admin class that injects ``renderer`` into its forms (idempotent).

    Recurses into ``inlines`` so inline forms are covered too.
    """
    if (
        issubclass(admin_class, RendererAdminMixin)
        and getattr(admin_class, "form_renderer", None) is renderer
    ):
        return admin_class

    wrapped = type(
        admin_class.__name__,
        (RendererAdminMixin, admin_class),
        {"form_renderer": renderer},
    )
    if getattr(admin_class, "inlines", None):
        wrapped.inlines = [
            with_renderer(inline, renderer) for inline in admin_class.inlines
        ]
    return wrapped


class RendererAdminSite(AdminSite):
    """
    An ``AdminSite`` that forces ``form_renderer`` onto every registered admin.

    Subclass it and set ``form_renderer`` to the renderer the admin should use.
    """

    form_renderer = None

    def register(self, model_or_iterable, admin_class=None, **options):
        admin_class = admin_class or ModelAdmin
        if self.form_renderer is not None:
            admin_class = with_renderer(admin_class, self.form_renderer)
        super().register(model_or_iterable, admin_class, **options)
