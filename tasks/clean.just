# run clean tasks
[group('clean')]
clean: clean-python clean-ruff

# clean lock file
[confirm]
[group('clean')]
clean-lock:
    rm -f uv.lock

# clean python files
[group('clean')]
clean-python:
    find . -type f -name '*.py[co]' -delete
    find . -type d -name __pycache__ -exec rm -r {} \+

# clean ruff folders
[group('clean')]
clean-ruff:
    rm -rf .ruff_cache/

# clean venv folder
[confirm]
[group('clean')]
clean-venv:
    rm -rf .venv/
