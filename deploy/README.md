# Deployment

This directory contains everything needed to run `evenki_tsakorpus2` in production
or for local development, using Docker Compose.

## Architecture

```
Internet
   │ https
   ▼
┌────────────────┐         ┌──────────────────────────────────┐
│  Host Apache   │         │  Docker stack (corpusnet bridge) │
│  (TLS, gisly.net)        │                                  │
└───────┬────────┘         │  ┌─────────┐    ┌──────────────┐ │
   /corpus → 127.0.0.1:8080│  │  nginx  │ ──►│  tsakorpus   │ │
                           └──┤  (:8080)│    │  (gunicorn,  │ │
                              │         │    │   :7342)     │ │
                              └────┬────┘    └──────┬───────┘ │
                                   │serves media     │         │
                                   ▼                 ▼         │
                              ┌─────────┐       ┌──────────────┐│
                              │./media/ │       │elasticsearch ││
                              │evenki/  │       │   (:9200,    ││
                              └─────────┘       │ internal)    ││
                                                └──────────────┘│
                              └──────────────────────────────────┘
```

- **Host Apache** (existing on gisly.net): terminates TLS, forwards `/corpus/*`
  to `127.0.0.1:8080` with `X-Forwarded-*` headers.
- **Docker nginx**: bound to `127.0.0.1:8080` only (not reachable from internet).
  Serves `/corpus/media/` from disk, caches static, rate-limits, basic-auth
  on `/corpus/admin`, proxies the rest to gunicorn.
- **tsakorpus**: Flask app under gunicorn (2 workers × 4 threads), mounted at
  `/corpus` via `DispatcherMiddleware` in `search/tsakorpus.py`.
- **Elasticsearch**: 7.17, single node, 1 GB heap, not exposed to host.

Tuned for a 4 GB RAM host:

| Container     | Mem cap | Notes                            |
| ------------- | ------- | -------------------------------- |
| elasticsearch | 1.7 GB  | JVM heap fixed at 1 GB           |
| tsakorpus     | 600 MB  | gunicorn, 2 workers × 4 threads  |
| nginx         | 100 MB  | tiny alpine image                |
| **Total**     | ~2.4 GB | ~1.5 GB left for OS + page cache |

## How the URL prefix works

`https://gisly.net/corpus/...` requires special handling because upstream
tsakorpus assumes mount-at-root. Two pieces make it work:

1. **`search/tsakorpus.py`** wraps the Flask app with werkzeug's
   `DispatcherMiddleware`, mounting it at `/corpus`. `url_for()` and the
   static-URL builder produce `/corpus/...` paths automatically. The prefix
   is configurable via the `TSAKORPUS_PREFIX` environment variable (set in
   `docker-compose.yml`).
2. **Templates** use relative URLs (`static/css/search.css`, `media/...`,
   `search_word`), which the browser resolves against the current page path.
   Verified zero absolute-path URLs in templates or JS.

To move to a different prefix or to root, change `TSAKORPUS_PREFIX` in
`docker-compose.yml`, the `/corpus` strings in `nginx/conf.d/tsakorpus.conf`
and `apache/gisly-corpus.conf`, and `elastic_url` in `conf/corpus.json` if
the corpus name is wrong (it isn't here).

---

## Production deployment (gisly.net)

Recommended host location: **`/srv/corpus/`**. The repo is cloned there
in its entirety; deployment commands run from `/srv/corpus/deploy/`.

### 1. Server prep

```bash
# Docker engine + compose plugin
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
                        docker-buildx-plugin docker-compose-plugin

# Required for Elasticsearch
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-elasticsearch.conf

# Apache modules for the reverse proxy
sudo a2enmod proxy proxy_http headers rewrite
sudo systemctl reload apache2

# Skip sudo for docker
sudo usermod -aG docker $USER && newgrp docker
```

### 2. Clone the repo

```bash
sudo mkdir -p /srv/corpus
sudo chown $USER:$USER /srv/corpus
cd /srv
git clone https://github.com/gisly/evenki_tsakorpus2.git corpus
cd /srv/corpus/deploy
```

### 3. Generate htpasswd for /corpus/admin

```bash
# From /srv/corpus/deploy/
docker run --rm httpd:2.4-alpine htpasswd -nbB elena 'your-strong-password' \
    > nginx/conf.d/htpasswd
```

The file is gitignored.

### 4. Hook up host Apache

Open your existing gisly.net vhost config (typically
`/etc/apache2/sites-available/gisly.net.conf` or similar), and inside the
`<VirtualHost *:443>` block paste the contents of `apache/gisly-corpus.conf`.

Test and reload:

```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### 5. Transfer data from the old server

```bash
# Media (audio/video). Adjust the source path if your old layout differs.
rsync -avzP --partial \
    user@old-server:/home/gisly/evenki_tsakorpus2/search/media/evenki/ \
    /srv/corpus/media/evenki/

# Corpus JSON (output of src_convertors)
rsync -avzP --partial \
    user@old-server:/home/gisly/evenki_tsakorpus2/corpus/evenki/ \
    /srv/corpus/corpus/evenki/
```

The `media/` directory is gitignored. `corpus/evenki/*.json.gz` is also
gitignored, so transferring won't dirty your working tree.

### 6. Start the stack

```bash
# From /srv/corpus/deploy/
docker compose up -d --build
docker compose ps                       # all three running/healthy
docker compose logs -f --tail=50        # watch warmup
```

### 7. Index the corpus

First time, and after every corpus update:

```bash
docker compose exec tsakorpus bash -c 'cd /app/indexator && python indexator.py'
```

The indexator reads `/app/corpus/evenki/*.json.gz` and writes to
`http://elasticsearch:9200`.

### 8. Verify

```bash
# Local: docker nginx is up
curl -I http://127.0.0.1:8080/corpus/

# Through Apache: TLS works and /corpus loads
curl -I https://gisly.net/corpus/

# ES indices present
docker compose exec elasticsearch curl -s 'localhost:9200/_cat/indices?v'
```

---

## Local desktop development

Same setup, but use the dev overlay so nginx is reachable from your browser
without needing Apache in front:

```bash
git clone https://github.com/gisly/evenki_tsakorpus2.git
cd evenki_tsakorpus2/deploy

# Generate htpasswd (admin will be needed even in dev)
docker run --rm httpd:2.4-alpine htpasswd -nbB elena 'devpassword' \
    > nginx/conf.d/htpasswd

# Bring up with the dev overlay
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Put corpus data in ../corpus/evenki/  and media in ../media/evenki/
# (paths relative to deploy/)

# Index
docker compose exec tsakorpus bash -c 'cd /app/indexator && python indexator.py'

# Open in browser: http://localhost:8080/corpus/
```

To make the dev overlay your default, set in your shell rc:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.dev.yml
```

Then `docker compose up -d` from `deploy/` Just Works for dev.

---

## Updating

The whole point of in-repo deployment: code and infrastructure update together.

```bash
cd /srv/corpus
git pull
cd deploy
docker compose build tsakorpus           # only if app code changed
docker compose up -d
```

If nginx/Apache configs changed in the pull, also:

```bash
docker compose restart nginx
sudo systemctl reload apache2
```

## Wiping the ES index

```bash
docker compose down
docker volume rm deploy_es_data          # name may differ -- `docker volume ls`
docker compose up -d
docker compose exec tsakorpus bash -c 'cd /app/indexator && python indexator.py'
```

## Backups

```bash
# ES index volume
docker run --rm -v deploy_es_data:/data -v "$(pwd):/backup" alpine \
    tar czf /backup/es_data_$(date +%F).tar.gz -C /data .

# Everything else worth keeping. (Code is in git, no need to back up.)
cd /srv/corpus
tar czf ~/backup_$(date +%F).tar.gz corpus/evenki media deploy/nginx/conf.d/htpasswd
```

See `HARDENING.md` for the post-deploy security checklist.
