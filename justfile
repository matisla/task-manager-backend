clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

start:
    docker compose up -d

test *args:
    uv run pytest {{ args }}

lint:
    uv run ruff check .

format:
    uv run ruff check --fix .
    uv run ruff format .

makemigrations msg:
    uv run alembic revision --autogenerate -m {{ msg }}

migrate:
    uv run alembic upgrade head
