# run install tasks
[group('install')]
install: install-project install-hooks

# install git hooks
[group('install')]
install-hooks:
    uv run pre-commit install

# install the project
[group('install')]
install-project:
    uv sync --all-groups
