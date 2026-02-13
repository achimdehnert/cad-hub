---
description: Deploy cad-hub (NL2CAD) to production server (88.198.191.108)
---

# Deploy CAD Hub to Production

## Prerequisites
- All changes committed and pushed to `main`
- Docker image built (CI builds automatically on push to main)

## Steps

1. SSH into server and pull latest code:
// turbo
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "cd /opt/cad-hub && git pull origin main 2>&1 | tail -5"'
```

2. Build Docker image on server:
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "cd /opt/cad-hub && DOCKER_BUILDKIT=1 docker build -f docker/app/Dockerfile -t ghcr.io/achimdehnert/cad-hub:latest . 2>&1 | tail -10"'
```

3. Restart containers with new image:
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "cd /opt/cad-hub && docker compose -f docker-compose.prod.yml up -d --force-recreate 2>&1 | tail -15"'
```

4. Wait and verify health:
// turbo
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "sleep 15 && docker logs cad-hub-web-1 --tail 5 2>&1"'
```

5. External health check:
// turbo
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "curl -s -o /dev/null -w %{http_code} https://nl2cad.de/livez/"'
```

## Rollback
If deployment fails, rollback to previous image:
```bash
wsl bash -c 'ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 root@88.198.191.108 "cd /opt/cad-hub && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml up -d 2>&1 | tail -10"'
```

## Infrastructure
- **URL**: https://nl2cad.de
- **Port**: 8094 → container 8000
- **Server**: 88.198.191.108 (`/opt/cad-hub`)
- **Image**: ghcr.io/achimdehnert/cad-hub:latest
- **Nginx**: /etc/nginx/sites-enabled/nl2cad.de.conf
- **SSL**: Let's Encrypt (auto-renew)
- **Containers**: web, worker, db (postgres:16), redis
