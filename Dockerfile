# Build the Svelte frontend
FROM node:22-bookworm-slim AS frontend-build

ARG BASE_PATH=/differential-cell-signaling
ENV BASE_PATH=${BASE_PATH}

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build
# Output is in /frontend/build


# Python backend + compiled frontend 
FROM python:3.13-bookworm

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (layer cache)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev

# Copy backend source
COPY backend/ .

# Copy the built frontend into the location FastAPI will serve it from
COPY --from=frontend-build /frontend/build ./build

EXPOSE 8000
ENV DATA_DIR=/app/data
ENV PATH="/app/.venv/bin:$PATH"

# CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]