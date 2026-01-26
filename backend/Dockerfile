FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app
ADD pyproject.toml /app
ADD uv.lock /app
RUN uv sync --locked
ADD . /app
EXPOSE 8000
ENV DATA_DIR=/app/data

ENV PATH="/app/.venv/bin:$PATH"

CMD [ "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]