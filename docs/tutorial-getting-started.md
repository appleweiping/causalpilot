# Run your first CausalPilot mission

This tutorial starts the local API and control room, runs the seeded fashion
mission, and shows how to confirm that the UI uses live API snapshots.

## Prerequisites

Install:

- Python 3.11 or newer;
- Node.js 22 with npm;
- Git.

Docker is optional.

## 1. Install dependencies

From the repository root:

```powershell
# Windows PowerShell
.\scripts\setup.ps1
```

```bash
# macOS or Linux
./scripts/setup.sh
```

The script creates `.venv/`, installs the backend in editable mode, and runs
`npm ci` from the checked-in lockfile.

## 2. Start both services

```powershell
# Windows PowerShell
.\scripts\run_demo.ps1
```

```bash
# macOS or Linux
./scripts/run_demo.sh
```

Open:

- control room: `http://127.0.0.1:3000`;
- interactive API: `http://127.0.0.1:8000/docs`;
- health check: `http://127.0.0.1:8000/health`.

Keep both services bound to the local interface. Press Ctrl+C in the launcher
terminal to stop them.

## 3. Run the mission

In the control room:

1. Start the 30,000-exposure fashion mission.
2. Inspect the four risk indices and the initial blocked deployment state.
3. Run the bounded randomized probe.
4. Inject drift and inspect the affected segment.
5. Answer the structured human question.
6. Deploy only an eligible segment or abstain.
7. Read the audit trail and reset the mission.

The action buttons reflect the snapshot's `allowed_actions`. A rejected action
does not change the mission.

## 4. Verify the evidence source

The UI displays an evidence-source badge. Confirm that it says `API`, then open
`http://127.0.0.1:8000/api/v1/mission/MISSION_ID` with the identifier shown in
the UI. The returned state and budget should match the control room.

If the badge says `simulation`, the browser has activated its deterministic
fallback. Check that the API is running and that
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## Offline visual mode

The hosted static demo deliberately uses the browser simulator. To reproduce
that mode locally, create `frontend/.env.local` with:

```dotenv
NEXT_PUBLIC_API_BASE_URL=offline
```

Then run:

```bash
npm --prefix frontend run dev
```

Delete `frontend/.env.local` before returning to the API-backed mode. Local env
files are ignored by Git.

## Docker mode

With Docker Compose installed:

```bash
docker compose up --build
```

The same ports are exposed. The containers run as unprivileged users with
read-only root filesystems. Stop them with Ctrl+C, then remove the stopped
containers with `docker compose down`.

## Run the tests

```bash
python -m pytest backend/tests evaluation/tests
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
```

Next, use [Run and verify the benchmark](how-to-run-benchmark.md) to produce
headless evidence artifacts.
