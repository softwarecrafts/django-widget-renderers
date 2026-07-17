# django-widget-renderers

**Let a `FormRenderer` decide which template each widget uses.**

Reference implementation of [django/new-features#172](https://github.com/django/new-features/issues/172).
Install it, try it, and please leave feedback on the issue — that's what this
package is for.

```python
class DrawerRenderer(TemplatesSetting):
    form_template_name  = "forms/drawer.html#form"     # Django already supports these
    field_template_name = "forms/drawer.html#field"    #

    text_input_template_name = "forms/drawer.html#text_input"   # this package adds these
    select_template_name     = "forms/drawer.html#select"
    textarea_template_name   = "forms/drawer.html#textarea"
```

That's the whole API. Widget templates get named the same way Django already
names form and field templates.

## The problem

Django picks a widget's template from the widget **class** (`Widget.template_name`).
So to restyle widgets across a project, you mutate that class attribute:

```python
forms.TextInput.template_name = "my/text_input.html"   # the status quo
```

This works. It's also **global** — you have now restyled every `TextInput` in the
process, including the ones in `django.contrib.admin`, whose JS-driven widgets
key off Django's stock markup. Restyle `Select` and the admin's autocomplete
breaks. Restyle `CheckboxInput` carelessly and the changelist's "select all"
quietly stops working.

The usual advice — subclass your widgets, write a custom template loader, or
shadow `django/forms/widgets/select.html` in your own template dir — all shares
the same ceiling:

> **A global mechanism gives you exactly one styling per widget class per
> process. Renderer scoping gives you N.**

Admin-vs-frontend is just the N=2 case that every project trips over. Drawer
forms, page forms, modal forms, a third-party form-styling package alongside your
own house style — that's N=4, and no loader can express it, because a loader
resolves on the template engine's global state and cannot know which renderer
asked.

## What this package does

Adds a `get_template_name` hook to `Widget` and wires it into `_render`, so the
template becomes a pure function of **(widget class, active renderer)**:

```python
def _render(self, template_name, context, renderer=None):
    if renderer is None:
        renderer = get_default_renderer()
    template_name = self.get_template_name(renderer, template_name)   # <- the only new line
    return mark_safe(renderer.render(template_name, context))
```

Now two renderers can style the same widget class differently, at the same time,
in one process:

```python
widget = forms.TextInput()
widget.render("f", "v", renderer=AlphaRenderer())   # <input class="alpha-input" ...>
widget.render("f", "v", renderer=BetaRenderer())    # <input class="beta-input" ...>
widget.render("f", "v", renderer=TemplatesSetting())  # Django's stock markup
```

## Install

```console
pip install django-widget-renderers
```

```python
INSTALLED_APPS = [
    ...,
    "django.forms",         # see below — easy to miss
    "widget_renderers",     # its AppConfig.ready() calls install()
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
```

Or call it yourself, if you want to control ordering:

```python
class MyAppConfig(AppConfig):
    def ready(self):
        from widget_renderers import install
        install()
```

The patch must be installed at startup — forms are *instantiated* before they're
*rendered*, so an import-time side effect elsewhere is too late.

Requires Django 4.2+ and Python 3.10+.

### You need `TemplatesSetting`, and therefore `django.forms`

Your renderer must resolve templates through your **project's** template engine,
which means basing it on `TemplatesSetting`. Django's default renderer
(`DjangoTemplates`) deliberately uses its own isolated engine that can't see your
template dirs, so a `select_template_name` pointing at `"forms/drawer.html"` would
never be found.

The catch: once you switch to `TemplatesSetting`, Django's *own* widget templates
have to be findable through your engine too — and they live inside the
`django.forms` app. If it isn't in `INSTALLED_APPS` (with `APP_DIRS: True`), every
widget you *haven't* styled blows up:

```
TemplateDoesNotExist: django/forms/widgets/textarea.html
```

So: add `django.forms` to `INSTALLED_APPS`, and keep `APP_DIRS: True` (or add
Django's form template directory to `DIRS` explicitly). This isn't specific to
this package — it's the standing requirement for `TemplatesSetting` — but you'll
almost certainly meet it here first. See
[Django's docs on `TemplatesSetting`](https://docs.djangoproject.com/en/stable/ref/forms/renderers/#templatessetting).

## Declaring a renderer

The attribute name is the snake_case of the widget class plus `_template_name` —
`TextInput` → `text_input_template_name`, `RadioSelect` → `radio_select_template_name`.

```python
from django.forms.renderers import TemplatesSetting

class WidgetsRenderer(TemplatesSetting):
    text_input_template_name = "forms.html#text_input"
    select_template_name = "forms.html#select"

class MyFormRenderer(WidgetsRenderer):
    # styled widgets PLUS styled form/field wrappers
    form_template_name = "forms.html#form"
    field_template_name = "forms.html#field"
```

Set `FORM_RENDERER = "myapp.renderers.MyFormRenderer"` as the project default, or
pass a renderer per form (`default_renderer = ...` / `MyForm(renderer=...)`).

> Template partials (`forms.html#text_input`) are Django 6.0+. On older versions
> just use whole template files.

## How resolution works

`get_template_name` walks the widget MRO. For each class it looks for
`<widget>_template_name` on the renderer; **first match wins**. A class that
defines its own `template_name` **short-circuits** the walk.

That one rule gives you Python's own attribute-shadowing semantics:

| Case | Result |
|---|---|
| `Select` + `select_template_name` | renderer's template |
| `SelectMultiple` (no own `template_name`) | resolves **up** to `select_template_name` |
| `MoneyInput(TextInput)` **with** its own `template_name` | keeps its own — a base override can't clobber it |
| ...but `money_input_template_name` is declared | renderer wins — shadowing isn't a lockout |
| renderer declares nothing | widget's own template, i.e. **stock Django** |

Two properties worth calling out:

- **Backwards compatibility is the default, not a feature.** Lookup is `getattr`
  against the renderer, so a renderer that declares nothing (a plain
  `TemplatesSetting`, or Django's `DjangoTemplates`) leaves every widget exactly
  where it was. There's no opt-out flag because none is needed.
- **Nothing user-controlled can steer a template.** The lookup key comes purely
  from the widget's *class* name — never `attrs`, instance state, or submitted
  data.
- **The hook is the extension point.** Override `get_template_name` on a widget
  to change resolution, or to log it while debugging.

A renderer is just an object; there's no base class to inherit and no resolver to
register.

## Admin

```python
from django.forms.renderers import TemplatesSetting
from widget_renderers import RendererAdminSite

class MyAdminSite(RendererAdminSite):
    form_renderer = TemplatesSetting   # declares nothing -> stock widgets
```

`register()` wraps each `ModelAdmin` (and its inlines) so the chosen renderer is
injected as the form's `default_renderer`, which beats the global `FORM_RENDERER`.
Your site stays styled; the admin stays stock.

## Limitations

Both are pinned as tests in `tests/test_limitations.py`.

**`MultiWidget` subwidgets aren't reached.** They're rendered from the parent's
context rather than via their own `render()`, so the hook never sees them. Style
the subwidget class directly, or give the MultiWidget a template naming the
subwidget templates it wants.

**Widgets rendered outside a form fall back to the global default.**
`Widget.render()` with no renderer uses `get_default_renderer()`. Scoping can't
help code that never passes a renderer — and Django itself has such code:
`ModelAdmin.action_checkbox` renders `CheckboxInput(attrs={"class": "action-select"})`
with no renderer, so it picks up your project default inside the admin. If your
template drops the caller's `class`, the changelist's "select all" breaks. (Ask
how we know.)

## Status

Beta, and deliberately narrow: it exists to test an idea proposed to Django. It
runs in production in a banking application, but the API is whatever the upstream
discussion decides it should be.

See [PROPOSAL.md](PROPOSAL.md) for what's actually being proposed to Django (a
method and one line), what's only scaffolding, and the alternatives considered.

## Licence

BSD-3-Clause — same as Django, so the code can be donated upstream without
friction.
