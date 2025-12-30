# SQLite Persistent Storage for k3s

## Overview

Add SQLite database with persistent storage to replace in-memory caching. Enables game history collection for playoff tiebreaker calculations.

## Goals

1. **Persistent cache** - Survive container restarts
2. **Game history** - Store all games for head-to-head lookups
3. **Efficient** - Single-file DB, no external services
4. **Simple ops** - Easy backup, portable data

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     k3s Node (Hetzner CX22)                      │
│                                                                  │
│  ┌────────────────┐    ┌────────────────┐                       │
│  │   Frontend     │───▶│    Backend     │                       │
│  │    :5000       │    │     :8000      │                       │
│  └────────────────┘    └────────────────┘                       │
│                               │                                  │
│                        ┌──────┴──────┐                          │
│                        │             │                          │
│                        ▼             ▼                          │
│              ┌──────────────┐   ┌─────────┐                     │
│              │ SQLite DB    │   │ ESPN    │                     │
│              │ /data/ls.db  │   │ API     │                     │
│              └──────────────┘   └─────────┘                     │
│                    │                                             │
│              ┌─────┴─────┐                                      │
│              │ hostPath  │  ← Simple, single-node storage       │
│              │ /opt/data │                                      │
│              └───────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Why SQLite

| Criteria | SQLite | Redis | PostgreSQL |
|----------|--------|-------|------------|
| Ops complexity | None | Medium | High |
| Memory overhead | ~0 | ~25MB | ~100MB |
| Persistence | File | Optional | Required |
| Backup | `cp ls.db ls.db.bak` | RDB dump | pg_dump |
| k8s resources | None | StatefulSet | StatefulSet |

For single-node k3s with light traffic, SQLite is ideal.

## Database Schema

```sql
-- Games: Core game data
CREATE TABLE games (
    id TEXT PRIMARY KEY,           -- ESPN game ID
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    season_type INTEGER NOT NULL,  -- 2=regular, 3=post
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    status TEXT NOT NULL,          -- scheduled, in_progress, final
    game_date TEXT NOT NULL,       -- ISO8601
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_games_season_week ON games(season, week);
CREATE INDEX idx_games_teams ON games(home_team, away_team);
CREATE INDEX idx_games_status ON games(status);

-- Standings: Snapshot per week
CREATE TABLE standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    team TEXT NOT NULL,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    ties INTEGER NOT NULL,
    division TEXT NOT NULL,
    conference TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(season, week, team)
);

CREATE INDEX idx_standings_lookup ON standings(season, week);

-- Cache metadata
CREATE TABLE cache_meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    expires_at TEXT
);
```

## Implementation Plan

### Phase 1: Backend Changes

#### 1.1 Add SQLite dependency

```toml
# pyproject.toml
[project]
dependencies = [
    # ... existing deps
    "aiosqlite>=0.19.0",  # Async SQLite for FastAPI
]
```

#### 1.2 Database module

```python
# backend/src/db.py
from pathlib import Path
import aiosqlite

DB_PATH = Path(os.getenv("DB_PATH", "/data/lightscore.db"))

async def get_db():
    """Get async database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    """Initialize database schema."""
    async with await get_db() as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
```

#### 1.3 Game repository

```python
# backend/src/games_repo.py
async def upsert_game(game: dict) -> None:
    """Insert or update game from ESPN data."""
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO games (id, season, week, season_type, home_team, away_team,
                              home_score, away_score, status, game_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                home_score = excluded.home_score,
                away_score = excluded.away_score,
                status = excluded.status,
                updated_at = datetime('now')
        """, (...))
        await db.commit()

async def get_head_to_head(team_a: str, team_b: str, season: int) -> list[dict]:
    """Get all games between two teams in a season."""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM games
            WHERE season = ?
              AND season_type = 2
              AND ((home_team = ? AND away_team = ?) 
                   OR (home_team = ? AND away_team = ?))
              AND status = 'final'
        """, (season, team_a, team_b, team_b, team_a))
        return [dict(row) for row in await cursor.fetchall()]
```

#### 1.4 Modify existing endpoints

```python
# backend/src/main.py

# Before: fetch from ESPN, cache in memory
# After: fetch from ESPN, store in DB, serve from DB

@app.get("/games/weekly")
async def get_weekly_games(week: int = None, season_type: int = 2):
    # 1. Check DB for recent data
    cached = await games_repo.get_cached_week(week, season_type)
    if cached and not is_stale(cached):
        return cached
    
    # 2. Fetch from ESPN
    fresh = await fetch_from_espn(week, season_type)
    
    # 3. Store in DB
    await games_repo.upsert_games(fresh)
    
    return fresh
```

### Phase 2: Kubernetes Changes

#### 2.1 HostPath volume (simplest for single-node)

```yaml
# k8s/base/backend-deployment.yaml
spec:
  template:
    spec:
      containers:
        - name: backend
          # ... existing config
          env:
            - name: DB_PATH
              value: "/data/lightscore.db"
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          hostPath:
            path: /opt/lightscore/data
            type: DirectoryOrCreate
```

#### 2.2 Init container for schema

```yaml
initContainers:
  - name: init-db
    image: ghcr.io/juusoi/light-score-backend:latest
    command: ["python", "-c", "from db import init_db; import asyncio; asyncio.run(init_db())"]
    volumeMounts:
      - name: data
        mountPath: /data
```

### Phase 3: Data Collection (Optional Enhancement)

#### 3.1 CronJob for historical backfill

```yaml
# k8s/base/game-collector-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: game-collector
  namespace: lightscore
spec:
  schedule: "0 * * * *"  # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: collector
              image: ghcr.io/juusoi/light-score-backend:latest
              command: ["python", "-m", "scripts.collect_games"]
              env:
                - name: DB_PATH
                  value: "/data/lightscore.db"
              volumeMounts:
                - name: data
                  mountPath: /data
          volumes:
            - name: data
              hostPath:
                path: /opt/lightscore/data
          restartPolicy: OnFailure
```

### Phase 4: Enhanced Tiebreaker Logic

```python
# backend/src/tiebreakers.py

async def calculate_tiebreaker(team_a: str, team_b: str, season: int) -> dict:
    """Calculate NFL tiebreaker between two teams."""
    
    # 1. Head-to-head
    h2h = await games_repo.get_head_to_head(team_a, team_b, season)
    if h2h:
        a_wins = sum(1 for g in h2h if winner(g) == team_a)
        b_wins = sum(1 for g in h2h if winner(g) == team_b)
        if a_wins != b_wins:
            return {"winner": team_a if a_wins > b_wins else team_b, 
                    "reason": "head-to-head"}
    
    # 2. Division record (already have from standings)
    # 3. Common games
    common = await games_repo.get_common_opponents(team_a, team_b, season)
    # ... continue tiebreaker chain
    
    return {"winner": None, "reason": "coin-flip"}
```

## Migration Steps

### Pre-requisites
- [ ] k3s migration complete (Phase 1 from hetzner-k8s.md)
- [ ] Application stable on k3s

### Implementation Order

1. **Local development first**
   ```bash
   # Add SQLite, test locally
   make mock-up
   # Verify games persist across restarts
   ```

2. **Deploy to k3s**
   ```bash
   kubectl apply -k k8s/overlays/prod
   ```

3. **Backfill historical data**
   ```bash
   # Run one-time job to fetch past weeks
   kubectl create job backfill --from=cronjob/game-collector -n lightscore
   ```

4. **Enable enhanced playoff picture**
   - Add tiebreaker display to frontend
   - Show head-to-head records

## Backup Strategy

```bash
# Simple backup (run on k3s node)
cp /opt/lightscore/data/lightscore.db /backup/lightscore-$(date +%Y%m%d).db

# Or from kubectl
kubectl exec -n lightscore deploy/backend -- \
  sqlite3 /data/lightscore.db ".backup /tmp/backup.db"
kubectl cp lightscore/backend-xxx:/tmp/backup.db ./backup.db
```

## Resource Estimates

| Resource | Without DB | With SQLite |
|----------|------------|-------------|
| Memory | ~128MB | ~130MB |
| Disk | ~50MB (image) | +~10MB/season |
| CPU | Same | Same |

SQLite adds negligible overhead.

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `aiosqlite` |
| `backend/src/db.py` | New - DB connection + schema |
| `backend/src/games_repo.py` | New - Game CRUD operations |
| `backend/src/main.py` | Use DB instead of memory cache |
| `backend/src/tiebreakers.py` | New - Tiebreaker calculations |
| `k8s/base/backend-deployment.yaml` | Add volume mount |
| `k8s/base/game-collector-cronjob.yaml` | New - Hourly data collection |

## Success Criteria

- [ ] Games persist across container restarts
- [ ] Cold start serves data from DB (no ESPN call)
- [ ] Head-to-head records available for any two teams
- [ ] Playoff picture shows tiebreaker explanations
- [ ] Backup/restore tested
