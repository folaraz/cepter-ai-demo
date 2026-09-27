# DataRoom Lens: one image serving the UI and the API (SPEC C12).
#   docker build -t dataroom-lens .
# Stage 1 builds frontend/dist; stage 2 is the Python runtime, with the embedding model
# downloaded at build time so the container never fetches anything when it runs.

# ---------- UI ----------
FROM node:22-slim AS ui
WORKDIR /repo/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY design /repo/design
COPY frontend ./
# The deployed UI talks to this service's API.
ARG VITE_USE_FIXTURES=false
ENV VITE_USE_FIXTURES=$VITE_USE_FIXTURES
RUN npm run build

# ---------- API ----------
FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH=/app/backend/.venv/bin:$PATH \
    EMBEDDING_CACHE_DIR=/app/models \
    FRONTEND_DIST=/app/frontend/dist \
    LLM_MODE=replay \
    ASK_LIVE=false
WORKDIR /app/backend

# Dependencies first, so code changes don't reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./
RUN uv sync --frozen --no-dev

COPY data/dataroom /app/data/dataroom
COPY evals /app/evals
COPY --from=ui /repo/frontend/dist /app/frontend/dist

RUN python -m app.retrieval.download
# From here on the model comes from the cache only: nothing is fetched at runtime.
ENV HF_HUB_OFFLINE=1

RUN useradd --system --uid 1001 lens && chown -R lens /app/models /app/evals
USER lens

EXPOSE 8000
# Railway sets PORT. The release step (`lens release`) runs before this as the
# pre-deploy command; see backend/README.md.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log --proxy-headers --forwarded-allow-ips '*'"]
