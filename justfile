clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    rm -f tests/database.db tests/debug.log

test *args:
    uv run pytest {{ args }}

lint:
    uv run ruff check .

format:
    uv run ruff check --fix .
    uv run ruff format .

start:
    docker compose up --build -d

log:
    docker compose logs app

build:
    docker compose build app

makemigrations msg:
    uv run alembic revision --autogenerate -m {{ msg }}

migrate:
    uv run alembic upgrade head
