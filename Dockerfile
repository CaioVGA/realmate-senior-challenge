FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM python:3.11-slim AS runner

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

COPY .entrypoints/*.sh /
RUN chmod +x /*.sh

COPY ./src ./src
COPY ./data ./data

EXPOSE 8000
ENTRYPOINT ["sh", "/django-entrypoint.sh"]
