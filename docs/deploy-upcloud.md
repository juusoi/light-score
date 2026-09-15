# Deployment (UpCloud Ubuntu Server)

This document describes deploying and operating Light Score on an UpCloud Ubuntu Cloud Server using rootless Podman, Caddy reverse proxy, and UFW.

## Architecture

```
Internet (HTTP:80, HTTPS:443)
       │
       ▼
   UFW Firewall (Allows 22, 80, 443; Denies direct public access to 5000/8000)
       │
       ▼
  Caddy Reverse Proxy (Host service, /etc/caddy/Caddyfile)
       │  Proxies to http://127.0.0.1:5000
       │  Handles automatic Let's Encrypt TLS & HTTP->HTTPS redirects
       ▼
┌─────────────────────────────────────────────────────────────┐
│  Rootless Podman (deployer user)                            │
│  Stack: ~/light-score/compose.prod.yaml                     │
│                                                             │
│   Frontend Container (Flask/Gunicorn)                       │
│   - Port: 127.0.0.1:5000:5000 (Loopback only)               │
│   - Env: BACKEND_URL=http://backend:8000                    │
│   - Memory: ~60-80 MB                                       │
│         │                                                   │
│         ▼                                                   │
│   Backend Container (FastAPI/Uvicorn)                       │
│   - Port: 8000 (Internal to Podman network light-score-net) │
│   - Memory: ~40-60 MB                                       │
└─────────────────────────────────────────────────────────────┘
  Total stack footprint: ~150-180 MB on 1 vCPU / 1 GB RAM server
```

## Resource Budget & Build Strategy

Because the server is provisioned with 1 vCPU and 1 GB RAM:
- **Zero in-situ image builds**: Images are built exclusively on GitHub Actions runners (2–4 vCPUs, 7–16 GB RAM) and pushed to GitHub Container Registry (`ghcr.io`).
- **Server workload**: The UpCloud server only pulls lightweight pre-built layers and starts the containers, preventing OOM crashes.

---

## Server Prerequisites & Setup

### 1. User Linger for Rootless Podman
Rootless Podman requires systemd user linger so containers continue running after the SSH session disconnects:

```bash
sudo loginctl enable-linger deployer
```

Confirm linger status:
```bash
loginctl show-user deployer | grep Linger
# Expected: Linger=yes
```

### 2. Firewall Rules (UFW)
Only ports 22, 80, and 443 should be open:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

### 3. Caddy Reverse Proxy
Place the configuration in `/etc/caddy/Caddyfile` (reference: [`deploy/Caddyfile`](file:///deploy/Caddyfile)):

```caddyfile
light-score.com {
    encode gzip zstd

    reverse_proxy 127.0.0.1:5000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    log {
        output file /var/log/caddy/light-score.access.log {
            roll_size 10mb
            roll_keep 3
        }
    }
}
```

Reload Caddy after making changes:
```bash
sudo systemctl reload caddy
```

---

## CI/CD Pipeline (GitHub Actions)

Workflow: [`.github/workflows/deploy-upcloud.yaml`](file:///.github/workflows/deploy-upcloud.yaml)

### GitHub Secrets Required:

| Secret | Description | Example |
| :--- | :--- | :--- |
| `UPCLOUD_HOST` | Public IPv4 address of the UpCloud server | `94.237.x.x` |
| `UPCLOUD_USER` | Deployment user | `deployer` |
| `UPCLOUD_SSH_KEY` | Private SSH key matching `deployer`'s `~/.ssh/authorized_keys` | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### Deployment Flow:
1. Triggered on merge to `main` after CI & Security checks pass, or manually via `workflow_dispatch`.
2. Multi-stage build for backend & frontend pushed to `ghcr.io/juusoi/light-score-backend:<sha>` and `frontend:<sha>`.
3. Action copies `compose.prod.yaml` and `scripts/deploy-upcloud.sh` to `~/light-score/`.
4. Executes deployment script: pulls images, brings up containers with `--remove-orphans`, and verifies `http://127.0.0.1:5000/`.

---

## Manual Verification & Operations

### Test Service Locally on Server:
```bash
# Verify frontend
curl -I http://127.0.0.1:5000/

# Verify backend communication through frontend
curl -s http://127.0.0.1:5000/ | grep -i "teletext"
```

### Inspect Running Containers:
```bash
podman ps
podman compose -f ~/light-score/compose.prod.yaml logs -f
```

### Check Caddy Logs:
```bash
journalctl -u caddy -n 50 -f
```

---

## Zero-Downtime Migration & Cutover

Because the AWS Lightsail deployment remains fully active:
1. **Verify UpCloud Out-of-Band**:
   - Query UpCloud server with custom host header:
     ```bash
     curl -k -H "Host: light-score.com" https://<UPCLOUD_IP>/
     ```
   - (Optional) Configure a temporary staging subdomain in Caddy to verify TLS.
2. **DNS Cutover**:
   - Lower DNS TTL to 300s.
   - Change the DNS A record for the domain to point to UpCloud's IP.
   - Caddy automatically obtains the Let's Encrypt TLS certificate upon first request.
3. **Rollback Safety**:
   - Keep AWS Lightsail running for 48–72 hours.
   - If any issues arise, immediately revert the DNS A record to Lightsail.
4. **Decommission**:
   - After 72 hours of validated traffic on UpCloud, decommission Lightsail container service.
