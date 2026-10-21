FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"

ENV PYTHONPATH="/app"

ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080

CMD ["python", "-m", "streamlit", "run", "src/main.py"]