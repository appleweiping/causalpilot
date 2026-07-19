# CausalPilot backend

Python 3.11+ and no API key are required.

```bash
python -m pip install -e "backend[test]"
python -m uvicorn causalpilot.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI UI. A minimal demo
episode is `POST /api/v1/mission/start`, repeated `POST /api/v1/mission/step`,
`POST /api/v1/mission/human-answer`, and `POST /api/v1/mission/drift`. The
in-memory store is intentionally local-demo scope; every statistical result is
computed from seeded row-level data and every transition is appended to the
mission audit trail.

Run verification with:

```bash
PYTHONPATH=backend python -m pytest backend/tests
```
