# Tsakorpus Flask app, served by gunicorn.
# Build context is the REPO ROOT (..), not deploy/.
# That's so we can COPY the application source directly, and so the
# .dockerignore at the repo root applies.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for lxml + curl for healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so this layer caches independently of source.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir gunicorn==21.2.0

# Shrink final image.
RUN apt-get purge -y build-essential libxml2-dev libxslt1-dev \
    && apt-get autoremove -y \
    && apt-get clean

# Copy application code. Bind mounts in docker-compose overlay conf/,
# corpus/, media/, and search/tmp/ at runtime so updates don't need a rebuild.
COPY . /app

# Runtime dirs (in case bind mounts don't create them).
RUN mkdir -p /app/search/tmp /app/media /app/corpus

# Non-root user. Keeps to UID 1000 to match the typical first user
# on Ubuntu hosts -- avoids permission grief on bind-mounted media.
RUN useradd -m -u 1000 tsakorpus \
    && chown -R tsakorpus:tsakorpus /app
USER tsakorpus

WORKDIR /app/search

EXPOSE 7342

# 2 workers x 4 threads is the sweet spot for a 4 GB host. Each worker
# loads the full Flask app + a connection pool to ES. --timeout 120 lets
# long ES queries finish (query_timeout in corpus.json is 60s).
CMD ["gunicorn", \
     "--bind", "0.0.0.0:7342", \
     "--workers", "2", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "tsakorpus:application"]
