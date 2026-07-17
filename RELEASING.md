# Releasing

Publishing runs on **PyPI Trusted Publishing** (OIDC): GitHub Actions proves its
identity to PyPI directly, so there is no API token stored in the repo, in
secrets, or on anyone's laptop. Nothing to rotate, nothing to leak.

## One-time PyPI setup

The project doesn't exist on PyPI yet, so register a **pending publisher** — this
reserves the name *and* authorises the workflow in one step. You must do this
before the first release; the workflow cannot bootstrap itself.

Go to <https://pypi.org/manage/account/publishing/> and add a new pending
publisher with **exactly** these values:

| Field | Value |
|---|---|
| PyPI Project Name | `django-widget-renderers` |
| Owner | `softwarecrafts` |
| Repository name | `django-widget-renderers` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

The environment name matters: `release.yml` declares `environment: pypi`, and
PyPI will reject the publish if they don't match.

Optionally, in the GitHub repo settings, create an environment named `pypi` and
add yourself as a required reviewer. Publishing then pauses for an explicit
approval click — a useful brake, given a version number can never be reused on
PyPI.

## Cutting a release

1. Bump `version` in `pyproject.toml`.
2. Commit and push to `main`. Wait for CI to be green.
3. Create a GitHub Release, tagged `vX.Y.Z` (the leading `v` is expected).

`release.yml` then builds, verifies the tag matches the version in
`pyproject.toml`, checks metadata with `twine`, and publishes.

The tag/version check exists because the two drift easily, and a mismatch on PyPI
is unfixable — you cannot re-upload a version, only yank it and burn a number.

## Verifying a release

```console
uv venv /tmp/check && VIRTUAL_ENV=/tmp/check uv pip install django-widget-renderers
/tmp/check/bin/python -c "import widget_renderers; print(widget_renderers.__all__)"
```

## Versioning

While the upstream proposal ([django/new-features#172][issue]) is under
discussion, treat the API as unstable and stay on `0.x`. The point of this
package is to test an idea; if the discussion lands on a different shape, this
follows it rather than defending its own history.

[issue]: https://github.com/django/new-features/issues/172
