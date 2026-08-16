FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src/ ./src/
COPY config.yaml ./
COPY scripts/ ./scripts/

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata curl

# Supercronic: zero-dependency cron designed for containers
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.46/supercronic-linux-amd64
ARG SUPERCRONIC_SHA256SUM=5adff01c5a797663948e656d2b61d10932369ee437eb5cb54fa872b2960f222b
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA256SUM}  supercronic-linux-amd64" | sha256sum -c - \
#    && tar -xzf supercronic-linux-amd64 \
#    && rm supercronic-linux-amd64 \
    && mv supercronic-linux-amd64 /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Cron tab for the validator (runs daily at 06:00 inside the container)
COPY crontab /crontab

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV TZ=Europe/Rome

EXPOSE 38080

CMD ["/bin/bash", "-c", "supercronic /crontab &>/dev/null & exec uv run bayesian-sprinkler"]