# ------------------- Stage 1: Build Stage ------------------------------
# We use Alpine for smaller image size (~329MB vs ~431MB for Debian slim).
# Trade-off: We must install build tools to compile native extensions (cryptography, etc.)
# since pre-built musl wheels aren't available. Debian -slim would skip compilation
# but produces a larger final image due to glibc wheel sizes.
FROM python:3.13-alpine AS build

# Install build dependencies for packages with native extensions (cryptography, etc.)
# https://cryptography.io/en/latest/installation/#building-cryptography-on-linux
RUN apk add --no-cache gcc g++ musl-dev python3-dev libffi-dev openssl-dev cargo pkgconfig

COPY --from=ghcr.io/astral-sh/uv:0.9.14 /uv /uvx /bin/

WORKDIR /code

# Copy dependency files and install dependencies (for layer caching)
# Note: We can't use --mount=type=cache since Azure Container Apps remote build doesn't support BuildKit:
# https://github.com/Azure/acr/issues/721
COPY uv.lock pyproject.toml ./
RUN uv sync --locked --no-install-project

# Copy the project and sync
COPY . .
RUN uv sync --locked

# ------------------- Stage 2: Final Stage ------------------------------
FROM python:3.13-alpine AS final

RUN addgroup -S app && adduser -S app -G app

COPY --from=build --chown=app:app /code /code

WORKDIR /code/servers
USER app

ENV PATH="/code/.venv/bin:$PATH"

EXPOSE 8000

ENV MCP_ENTRY=deployed

# Copy and use entrypoint script for clean env expansion
COPY --chown=app:app servers/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
