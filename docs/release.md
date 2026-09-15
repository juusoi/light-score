# Release
 
## Preconditions
 
- Main branch green (CI + security)
- Images built and pushed to GHCR (`ghcr.io/juusoi/light-score-*`)
 
## Tag
 
```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

## Deploy

Automated deployment runs via `podman-auto-update.timer` pulling the latest digests on the UpCloud server. Manual update trigger:
```bash
podman auto-update
```

## Rollback

- Native automatic rollback: if a pulled image fails container health checks, Podman automatically rolls back to the prior working image.
- Manual rollback: `podman auto-update --rollback` or tag/push the previous image digest to GHCR.

## Verify

- `curl -I https://light-score.com/`
- Check container status on host: `podman ps`
- Check systemd unit logs: `journalctl --user -u light-score-frontend.service -n 50`
