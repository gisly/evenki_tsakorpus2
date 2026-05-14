# Hardening checklist

You're redeploying after a compromise. Don't skip this.

## Likely vectors on the old setup

In rough order of probability for a Tsakorpus deployment:

1. **Exposed Elasticsearch on 9200.** ES 7.x ships with security disabled.
   If `network.host: 0.0.0.0` was set and 9200 was reachable, anyone could
   list/replace/delete indices (the "Meow attack"). The new setup does NOT
   bind 9200 to the host -- ES is only reachable inside the docker network.

2. **Unprotected `/admin`.** Tsakorpus admin routes can edit configuration.
   The new setup requires HTTP basic auth at docker-nginx. Optional second
   auth layer at host Apache below.

3. **SSH brute force / weak password.**

4. **Unpatched OS / Apache CVE.**

If you can dig through `/var/log/auth.log`, `/var/log/apache2/access.log`,
and `~/.bash_history` on the old box before decommissioning, you'll find out
which one.

## On the new server

### SSH

```bash
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

sudo apt-get install -y fail2ban
sudo systemctl enable --now fail2ban
```

### Firewall

Apache already exposes 80/443. Docker binds nginx to `127.0.0.1:8080`, not
publicly reachable, so no firewall changes needed for the docker stack.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Verify from outside that docker ports aren't exposed:

```bash
# From your laptop:
nmap -Pn -p 8080,9200,7342 gisly.net   # should all show 'filtered' or 'closed'
```

### Unattended security upgrades

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Apache hardening (if not already done)

```apache
# In your Apache config (apache2.conf or in security.conf):
ServerTokens Prod
ServerSignature Off
TraceEnable Off
```

## Application

- **Change the htpasswd password.** No default password in the new setup;
  `bootstrap.sh` no longer exists, so you must explicitly generate one.
- **`"debug": false`** in `conf/corpus.json` -- already set in the committed
  config.
- **Don't expose 7342 or 9200** -- the compose file is correct.
- **Don't bind nginx to 0.0.0.0** in production -- the compose file binds it
  to `127.0.0.1:8080`. (Only `docker-compose.dev.yml` opens it up, and only
  for desktop dev.)

## Optional: extra Apache-level protection for /corpus/admin

A second auth layer at host Apache means brute-force attempts never reach
the docker stack. Inside your gisly.net vhost, BEFORE the generic
`<Location "/corpus/">` from `deploy/apache/gisly-corpus.conf`:

```apache
<Location "/corpus/admin">
    AuthType Basic
    AuthName "Restricted"
    AuthUserFile /etc/apache2/htpasswd-corpus
    Require valid-user
</Location>
```

Generate: `sudo htpasswd -c /etc/apache2/htpasswd-corpus elena`.

## Optional: IP allowlist for /corpus/admin

If you only need admin from known locations, prefer this to passwords:

```apache
<Location "/corpus/admin">
    Require ip 203.0.113.42      # your home IP
</Location>
```

## Monitoring

```bash
# Apache access log
sudo tail -f /var/log/apache2/gisly-access.log | grep /corpus/

# Top hammers in the last hour
sudo awk '{print $1}' /var/log/apache2/gisly-access.log | sort | uniq -c | sort -rn | head

# ES heap usage
docker compose exec elasticsearch curl -s \
    'localhost:9200/_cat/nodes?v&h=name,heap.percent,ram.percent,cpu,load_1m'

# Brute-force attempts on /corpus/admin
docker compose logs nginx --since 1h | grep ' 401 '
```

If memory pressure gets bad: drop ES heap to 768m (edit `ES_JAVA_OPTS` in
`docker-compose.yml`) and gunicorn to 1 worker (edit `--workers` in `Dockerfile`).

## After all this

```bash
# Should show only 22, 80, 443
nmap -Pn -p- gisly.net

# Should be the corpus
curl -I https://gisly.net/corpus/

# Should be 401 (not 200, not 403, not 502)
curl -I https://gisly.net/corpus/admin/

# Should NOT return any ES response
curl -m 5 http://gisly.net:9200/ 2>&1 | head
```
