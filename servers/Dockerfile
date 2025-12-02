# ------------------- Stage 0: Base Stage ------------------------------
FROM python:3.13-alpine AS base

# Install tini, a tiny init for containers
RUN apk add --update --no-cache tini

# Install required packages for cryptography and ml-dtypes packages
# https://cryptography.io/en/latest/installation/#building-cryptography-on-linux
RUN apk add gcc g++ musl-dev python3-dev libffi-dev openssl-dev cargo pkgconfig

# ------------------- Stage 1: Build Stage ------------------------------
FROM base AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

# Install dependencies first (for layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project and sync
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# ------------------- Stage 2: Final Stage ------------------------------
FROM base AS final

RUN addgroup -S app && adduser -S app -G app

COPY --from=build --chown=app:app /code /code

WORKDIR /code/servers
USER app

ENV PATH="/code/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["tini", "uvicorn", "deployed_mcp:app", "--host", "0.0.0.0", "--port", "8000"]