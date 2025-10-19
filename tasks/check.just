# run check tasks
[group('check')]
check: check-lock check-code check-type check-format

# check code quality
[group('check')]
check-code:
    uv run ruff check {{AGENT}}

# check code format
[group('check')]
check-format:
    uv run ruff format --check {{AGENT}}

# check code lock
[group('check')]
check-lock:
    uv lock --check

# check code type
[group('check')]
check-type:
    uv run ty check {{AGENT}}
