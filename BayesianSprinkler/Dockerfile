FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src/ ./src/
COPY config.yaml ./

ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["uv", "run", "bayesian-sprinkler"]