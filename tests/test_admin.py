"""
Admin integration -- the N=2 case, and why it motivates the proposal.

``django.contrib.admin``'s JS-driven widgets key off Django's stock markup, so a
project that restyles widgets globally breaks them. Scoping the styling to a
renderer lets the admin keep stock markup while the rest of the site is styled.
"""

import pytest
from django.contrib.admin import AdminSite
from django.contrib.admin import ModelAdmin
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import User
from django.test import RequestFactory

from tests.conftest import AlphaRenderer
from tests.conftest import StockRenderer
from widget_renderers import RendererAdminMixin
from widget_renderers import RendererAdminSite
from widget_renderers import with_renderer

pytestmark = pytest.mark.django_db


@pytest.fixture
def request_():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    return request


class TestWithRenderer:
    def test_wraps_an_admin_class(self):
        wrapped = with_renderer(ModelAdmin, StockRenderer)
        assert issubclass(wrapped, RendererAdminMixin)
        assert wrapped.form_renderer is StockRenderer

    def test_is_idempotent(self):
        wrapped = with_renderer(ModelAdmin, StockRenderer)
        assert with_renderer(wrapped, StockRenderer) is wrapped

    def test_recurses_into_inlines(self):
        class Inline(ModelAdmin):
            pass

        class Parent(ModelAdmin):
            inlines = [Inline]

        wrapped = with_renderer(Parent, StockRenderer)
        assert issubclass(wrapped.inlines[0], RendererAdminMixin)
        assert wrapped.inlines[0].form_renderer is StockRenderer

    def test_injects_default_renderer_onto_the_form(self, request_):
        admin = with_renderer(ModelAdmin, StockRenderer)(User, AdminSite())
        assert admin.get_form(request_).default_renderer is StockRenderer


class TestRendererAdminSite:
    def test_register_applies_the_sites_renderer(self):
        class Site(RendererAdminSite):
            form_renderer = StockRenderer

        site = Site(name="stock-admin")
        site.register(User)
        assert isinstance(site._registry[User], RendererAdminMixin)
        assert site._registry[User].form_renderer is StockRenderer

    def test_admin_keeps_stock_markup_while_the_site_is_styled(self, request_):
        """The motivating case, end to end: the project default is styled, the
        admin is not, and both are live at once."""

        class Site(RendererAdminSite):
            form_renderer = StockRenderer

        site = Site(name="stock-admin-2")
        site.register(User)
        admin_form = site._registry[User].get_form(request_)()
        admin_html = str(admin_form["username"])

        # Same field, same widget class, styled renderer -> different markup.
        styled_html = admin_form.fields["username"].widget.render(
            "username", "", renderer=AlphaRenderer()
        )

        assert "alpha-input" not in admin_html  # admin stays stock
        assert "alpha-input" in styled_html  # the site is styled
