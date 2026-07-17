# What is actually being proposed to Django

Tracking issue: [django/new-features#172](https://github.com/django/new-features/issues/172)

This package is deliberately larger than the proposal. Most of it is scaffolding
that exists only because a third-party package cannot edit Django. This document
separates the two, so the size of the actual ask is not in doubt.

## The ask

One new method on `Widget`, and one line in `Widget._render`.

```diff
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@
+    def get_template_name(self, renderer, template_name):
+        """Return the template `renderer` wants for this widget."""
+        for klass in type(self).__mro__:
+            override = getattr(renderer, f"{widget_slug(klass)}_template_name", None)
+            if override is not None:
+                return override
+            if "template_name" in klass.__dict__:
+                break
+        return template_name
+
     def _render(self, template_name, context, renderer=None):
         if renderer is None:
             renderer = get_default_renderer()
+        template_name = self.get_template_name(renderer, template_name)
         return mark_safe(renderer.render(template_name, context))
```

Plus a helper for the naming convention (`TextInput` → `text_input`):

```python
_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")

def widget_slug(widget_class):
    return _CAMEL_BOUNDARY.sub("_", widget_class.__name__).lower()
```

No new classes. No changes to `BaseRenderer`, `TemplatesSetting`, or any widget.
No new setting. No deprecation.

## What is only scaffolding

| Module | In-tree? | Why it exists here |
|---|---|---|
| `patches.get_template_name` + the `_render` line | **the proposal** | — |
| `patches.install()` | no | Django's built-in widgets can't be made to inherit a custom base, so patching `Widget` is the only way to apply this out-of-tree. |
| `admin.py` (`RendererAdminSite`, `with_renderer`) | no | In-tree, `django.contrib.admin` would simply declare its own renderer. This shim retrofits that from outside. |
| `apps.py` | no | Somewhere has to call `install()` at startup. |

## Why

Django resolves a widget's template from the widget **class**. Overriding that
globally is the only supported route, and global is the problem:

> A global mechanism gives you exactly one styling per widget class per process.
> Renderer scoping gives you N.

`django.contrib.admin` is the N=2 case every project meets: its JS widgets depend
on stock markup, so any project-wide restyle breaks them. Beyond N=2 sits the
thing this actually unlocks — **form-styling packages that compose**. Ship
templates plus a `FormRenderer` subclass, and a project can use yours for some
forms, its own for others, and stock in the admin, with no global namespace to
fight over. That ecosystem is not currently expressible.

`tests/test_scoping.py` pins this, including a test that demonstrates the status
quo (mutating `template_name`) leaking into every consumer at once.

## Objections raised, and answers

These are the concerns raised on the issue by @codingjoe, who implemented
Django's template-based form rendering. Each has a corresponding test.

### "Template names determined by instance, not class"

A misreading of the original sketch, but worth closing off permanently: the
lookup key is derived **purely from the widget's class name**, via
`type(self).__mro__`. Instance state, `attrs`, and submitted data are never
consulted.

→ `test_resolution.py::test_lookup_key_never_comes_from_instance_or_user_data`

### "Opens the door for injection vectors"

Follows from the above. Template names come from renderer **class attributes**,
which are developer-authored, and from the widget's own `template_name`. There is
no path from user input to a template name.

→ same test.

### "Will make debugging form rendering harder"

Resolution is a single pure function with one rule, and it's an overridable hook:
subclass and override `get_template_name` to trace or change it. It is also
unit-testable without rendering anything — arguably *easier* to debug than the
status quo, where resolution is an implicit class attribute mutated at import
time from who-knows-where.

→ `test_resolution.py::test_hook_is_overridable`

### "It's already pretty complex"

Fair, and the reason the diff above is the whole ask. Nothing is added to the
renderer API; the convention (`<widget>_template_name`) is the one Django already
uses for `form_template_name` and `field_template_name`, so there's no new
concept to learn.

### "Just override template loading — it wouldn't require adjustments to the current Django API"

True, and it already works today — which is why it isn't the proposal. A loader
resolves on the template engine's global state: it cannot know *which* renderer
asked, so it can only give one answer per process. The requirement is two
answers, simultaneously, in one process (styled site + stock admin), and more
than two once form-styling packages compose.

→ `test_scoping.py::TestWhyGlobalIsInsufficient`

### "Follow `TemplateView` — use multiple names from specific to generic"

The **instinct is right**, and this proposal already implements it — the MRO walk
*is* specific→generic. The difference is where the ordering comes from: Python's
class hierarchy derives it (`SelectMultiple` → `Select` → `Widget`) rather than a
developer hand-maintaining a name list.

Doing it as a literal `get_template_names()` list would mean probing the
filesystem for template existence on every widget render, which conflates "which
template do I want" with "does it exist", and costs a loader hit per candidate.
The renderer already knows exactly which template it wants — no probing needed.

More decisively: a name list is still resolved by the engine, so it inherits the
same global ceiling. It cannot express "stock in the admin, styled everywhere
else" either.

## Open questions for the Django discussion

1. **Naming.** `<widget>_template_name` matches the existing `form_template_name`
   convention. The original issue's example used snake_case but its sketch used
   `self.__class__.__name__` (i.e. `Select_template_name`) — this package settles
   on snake_case.
2. **Hook placement.** On `Widget` (here) or on the renderer
   (`renderer.get_widget_template(widget, name)`)? Widget-side keeps "a renderer
   is any object with attributes" true and needs no `BaseRenderer` change;
   renderer-side is arguably more coherent but is a bigger diff and would break
   third-party renderers not inheriting `BaseRenderer`.
3. **Shadowing rule.** A widget defining its own `template_name` short-circuits
   the MRO walk. This is what preserves custom widgets, but it means
   `text_input_template_name` deliberately won't reach `MoneyInput(TextInput)`.
   Naming the subclass explicitly still works. Is that the right default?
4. **`MultiWidget`.** Subwidgets render from the parent's context and so are out
   of reach. Should `MultiWidget.get_context` consult the renderer for subwidget
   templates too?
5. **Widgets rendered without a renderer.** `Widget.render()` with no renderer
   falls back to the global default — including Django's own
   `ModelAdmin.action_checkbox`. Should such call sites pass a renderer?

## Prior art

- [`django-form-renderers`](https://pypi.org/project/django-form-renderers/) —
  adds render methods and BEM classes to widgets. Same pain, opposite approach:
  it changes the widgets. This proposal leaves widgets alone and moves the
  decision to the renderer.
- Django's own form-rendering revamp (4.1) introduced `form_template_name` /
  `field_template_name` on renderers. This is the same idea, applied one level
  down.

## Evidence

- Runs in production in a banking application (styled frontend + stock admin).
- Adopting the hook there changed **zero** rendered output across 84
  widget/renderer/form combinations, verified by byte-diffing rendered HTML
  before and after.
- The naive `self.__class__.__name__` lookup from the original sketch is
  insufficient: `SelectMultiple` inherits `Select.template_name`, so it would
  render stock while `Select` renders styled — a silent inconsistency. This was
  found by running it, and is why the MRO walk exists.
  → `test_resolution.py::test_unstyled_subclass_resolves_up_the_mro`
