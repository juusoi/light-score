# UpCloud Migration Plan: Pull-Based Podman Auto-Update (Quadlets) + Caddy + UFW

## 1. Environment & Architecture Overview

The target environment is a **1 vCPU / 1 GB RAM UpCloud Ubuntu Cloud Server**:
- **Target OS**: Ubuntu Linux
- **Resources**: 1 vCPU, 1 GB RAM (All image builds offloaded to GitHub Actions)
- **Container Engine**: Rootless Podman Quadlets under the `deployer` user with `AutoUpdate=registry`
- **Update Mechanism**: Native `podman-auto-update.timer` (pull-based, zero SSH keys in GitHub)
- **Reverse Proxy / TLS**: Caddy (running on host, managing Let's Encrypt TLS)
- **Firewall**: UFW (ports 22, 80, 443 open; ports 5000 & 8000 closed to public)
- **AWS Lightsail**: Stays running in parallel during migration for zero risk.

```
GitHub Actions: Push to main → CI & Security pass → Build & Push to ghcr.io:latest
                                                              │
                                                              │ (Pull-based polling)
                                                              ▼
UpCloud Server (deployer @ Ubuntu)
┌─────────────────────────────────────────────────────────────┐
│  podman-auto-update.timer (Checks ghcr.io for new digests)  │
│                                                             │
│  Rootless Podman Quadlets (~/.config/containers/systemd/)   │
│  Network: light-score-net                                   │
│                                                             │
│   Frontend Container (Flask/Gunicorn)                       │
│   - Image: ghcr.io/juusoi/light-score-frontend:latest       │
│   - AutoUpdate: registry                                    │
│   - Port: 127.0.0.1:5000:5000 (Loopback only)               │
│   - Env: BACKEND_URL=http://light-score-backend:8000        │
│         │                                                   │
│         ▼                                                   │
│   Backend Container (FastAPI/Uvicorn)                       │
│   - Image: ghcr.io/juusoi/light-score-backend:latest        │
│   - AutoUpdate: registry                                    │
│   - Port: 8000 (Internal only)                             │
└─────────────────────────────────────────────────────────────┘
       ▲
       │ Proxies 127.0.0.1:5000 (Automatic Let's Encrypt TLS)
  Caddy Reverse Proxy (Host, /etc/caddy/Caddyfile)
       ▲
       │
  UFW Firewall (Allows 80, 443, 22)
       ▲
       │
  Internet
```

---

## 2. Advantages of the Pull-Based Model for 1 CPU / 1 GB RAM

1. **Zero Build Workload on Host**: Building on 1 GB RAM can trigger Linux OOM. Pre-building in GitHub Actions solves this completely.
2. **Zero Credentials in GitHub**: No SSH keys, no host IPs, and no deploy passwords exist in GitHub Secrets.
3. **Zero Inbound Port Exposure for CI**: The server does not accept incoming SSH connections from CI.
4. **Native Health & Rollback**: `podman auto-update` checks container health; if the updated container fails to start, Podman rolls back to the previous image automatically.
5. **Systemd Native**: Containers are managed as first-class systemd services via Podman Quadlets (`light-score-frontend.service` and `light-score-backend.service`).

---

## 3. Server Setup Procedure (One-Time)

### 3.1 Enable Linger
```bash
sudo loginctl enable-linger deployer
```

### 3.2 Install Quadlet Units
Copy files from `deploy/quadlet/` to `~/.config/containers/systemd/`:
- `light-score.network`
- `light-score-backend.container`
- `light-score-frontend.container`

```bash
mkdir -p ~/.config/containers/systemd
cp deploy/quadlet/* ~/.config/containers/systemd/
```

### 3.3 Start Services & Enable Timer
```bash
systemctl --user daemon-reload
systemctl --user start light-score-frontend.service
systemctl --user enable --now podman-auto-update.timer
```

---

## 4. GitHub Actions CI/CD (`deploy-upcloud.yaml`)

Triggered on `main` after CI and Security pass:
1. Builds backend and frontend multi-stage images on GitHub-hosted runners.
2. Pushes `ghcr.io/juusoi/light-score-backend:latest` and `frontend:latest` (plus SHA tags).
3. The UpCloud server's `podman-auto-update.timer` detects the new image digest and restarts the services automatically.
