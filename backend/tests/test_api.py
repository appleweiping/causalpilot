from fastapi.testclient import TestClient

from causalpilot.main import app


client = TestClient(app)


def start(seed: int = 42) -> dict:
    response = client.post("/api/v1/mission/start", json={"seed": seed})
    assert response.status_code == 200
    return response.json()


def test_health_and_openapi_contract():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["deterministic_mode"] is True
    openapi = client.get("/openapi.json").json()
    paths = openapi["paths"]
    assert "/api/v1/mission/start" in paths
    assert "/api/v1/mission/step" in paths
    assert "/api/v1/mission/drift" in paths
    assert "/api/v1/mission/human-answer" in paths
    assert "/api/v1/mission/reset" in paths


def test_complete_http_episode_and_reset():
    snapshot = start()
    mission_id = snapshot["mission_id"]
    experiment = client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    assert experiment.status_code == 200
    assert experiment.json()["state"] == "experimenting"
    ask = client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    assert ask.json()["state"] == "awaiting_human"
    answer = client.post(
        "/api/v1/mission/human-answer",
        json={"mission_id": mission_id, "answer": "15%", "margin_floor": 0.15},
    )
    assert answer.json()["state"] == "ready_to_deploy"
    deploy = client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    assert deploy.json()["state"] == "deployed"
    reset = client.post("/api/v1/mission/reset", json={"mission_id": mission_id})
    new_mission_id = reset.json()["mission_id"]
    assert new_mission_id != mission_id
    assert reset.json()["state"] == "diagnosing"
    assert reset.json()["step"] == 0
    assert reset.json()["audit"][0]["details"]["parent_mission_id"] == mission_id
    assert client.get(f"/api/v1/mission/{mission_id}").json()["state"] == "deployed"


def test_pause_segment_api_and_deploy_all_gate():
    snapshot = start(seed=42)
    mission_id = snapshot["mission_id"]
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    client.post(
        "/api/v1/mission/human-answer",
        json={"mission_id": mission_id, "answer": "15%", "margin_floor": 0.15},
    )
    gated = client.post(
        "/api/v1/mission/step",
        json={"mission_id": mission_id, "requested_action": "deploy_all"},
    )
    assert gated.status_code == 409
    deployed = client.post("/api/v1/mission/step", json={"mission_id": mission_id}).json()
    target = next(segment["id"] for segment in deployed["segments"] if segment["status"] == "deployed")
    paused = client.post(
        "/api/v1/mission/step",
        json={
            "mission_id": mission_id,
            "requested_action": "pause_segment",
            "segment_id": target,
        },
    )
    assert paused.status_code == 200
    assert next(s for s in paused.json()["segments"] if s["id"] == target)["status"] == "paused"


def test_drift_and_sse():
    snapshot = start(seed=3)
    mission_id = snapshot["mission_id"]
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    client.post(
        "/api/v1/mission/human-answer",
        json={"mission_id": mission_id, "answer": "15%", "margin_floor": 0.15},
    )
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    response = client.post(
        "/api/v1/mission/drift",
        json={"mission_id": mission_id, "severity": 0.7, "segment_id": "new_arrivals"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "drift_detected"
    events = client.get(f"/api/v1/mission/{mission_id}/events")
    assert events.status_code == 200
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: audit" in events.text
    assert "event: end" in events.text


def test_human_answer_schema_is_semantically_bound():
    snapshot = start(seed=8)
    mission_id = snapshot["mission_id"]
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    client.post("/api/v1/mission/step", json={"mission_id": mission_id})
    rejected = client.post(
        "/api/v1/mission/human-answer",
        json={"mission_id": mission_id, "answer": "yes"},
    )
    assert rejected.status_code == 409
    assert "margin_floor" in rejected.json()["detail"]


def test_api_reports_missing_mission_and_invalid_action():
    missing = client.get("/api/v1/mission/not-a-real-mission")
    assert missing.status_code == 404
    snapshot = start()
    invalid = client.post(
        "/api/v1/mission/step",
        json={"mission_id": snapshot["mission_id"], "requested_action": "segment_deploy"},
    )
    assert invalid.status_code == 409
