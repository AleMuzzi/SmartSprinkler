FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src/ ./src/
COPY config.yaml ./
COPY scripts/ ./scripts/

# Supercronic: zero-dependency cron designed for containers
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64.tar.gz
ARG SUPERCRONIC_SHA1SUM=80c6acaafb9ae8d77f1da6bf6a916cc343539a97
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  supercronic-linux-amd64" | sha1sum -c - \
    && tar -xzf supercronic-linux-amd64 \
    && rm supercronic-linux-amd64 \
    && mv supercronic /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Cron tab for the validator (runs daily at 06:00 inside the container)
COPY crontab /crontab

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["/bin/bash", "-c", "supercronic /crontab &>/dev/null & exec uv run bayesian-sprinkler"]