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

# Wait-for-ES entrypoint: blocks gunicorn until Elasticsearch answers
# green/yellow, so a host reboot (which starts all containers in parallel,
# ignoring compose depends_on) can't start the app before ES is up and
# leave it serving the cached "technical issues" page. Copied explicitly
# so it doesn't depend on where in the repo tree the file lives.
COPY deploy/wait-for-es.py /usr/local/bin/wait-for-es.py

# Runtime dirs (in case bind mounts don't create them).
RUN mkdir -p /app/search/tmp /app/media /app/corpus \
    && chmod +x /usr/local/bin/wait-for-es.py

# Non-root user. Keeps to UID 1000 to match the typical first user
# on Ubuntu hosts -- avoids permission grief on bind-mounted media.
RUN useradd -m -u 1000 tsakorpus \
    && chown -R tsakorpus:tsakorpus /app
USER tsakorpus

WORKDIR /app/search

EXPOSE 7342

# Gate startup on ES being reachable, then exec the real command.
# ENTRYPOINT wraps CMD: the wait script runs first, then execvp's gunicorn.
ENTRYPOINT ["python3", "/usr/local/bin/wait-for-es.py"]

# 1 worker x 4 threads is the sweet spot for a 4 GB host. Each worker
# loads the full Flask app + a connection pool to ES. --timeout 120 lets
# long ES queries finish (query_timeout in corpus.json is 60s).
CMD ["gunicorn", \
     "--bind", "0.0.0.0:7342", \
     "--workers", "1", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "tsakorpus:application"]
