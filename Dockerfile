FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (kept minimal). build-essential is not required for this stack.
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md wsgi.py ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir .
RUN chmod +x /app/scripts/docker_entrypoint.sh

EXPOSE 8000

CMD ["/app/scripts/docker_entrypoint.sh"]
