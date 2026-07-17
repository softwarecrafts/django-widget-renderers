"""Test matrix. `pip install nox` then `nox`."""

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

# Django's own supported Python versions per release.
MATRIX = {
    "4.2": ["3.10", "3.11", "3.12"],
    "5.2": ["3.10", "3.11", "3.12", "3.13"],
    "6.0": ["3.12", "3.13"],
}

PARAMS = [(python, django) for django, pythons in MATRIX.items() for python in pythons]


@nox.session
@nox.parametrize("python,django", PARAMS, ids=[f"py{p}-dj{d}" for p, d in PARAMS])
def tests(session, django):
    session.install("-e", ".")
    session.install(f"Django~={django}.0", "pytest", "pytest-django")
    session.run("pytest", *session.posargs)


@nox.session(python="3.13")
def lint(session):
    session.install("ruff")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
