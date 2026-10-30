# A library with no server or database: dev, stop and seed are here for the project contract.
dev:
    @echo "django-widget-renderers has no dev server; use just test"

stop:
    @echo "nothing to stop"

seed:
    @echo "no database to seed"

# One Django and Python; `uvx nox` runs the full matrix.
test *ARGS:
    uv run --with pytest --with pytest-django pytest {{ ARGS }}
