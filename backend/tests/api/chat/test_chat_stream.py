"""SSE-01..04, SSE-06, RBAC-08, RBAC-10 and the history routes over HTTP."""

import json

from app.api.sse import EVENT_MODELS
from app.llm.tasks import Task
from tests.api.conftest import login
from tests.graph.conftest import base_script

ANSWER = {Task.ANSWER: lambda s, u: "**Global Automation Inc.** leads."}


def parse_sse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def stream(client, **body):
    response = client.post("/api/chat/stream", json=body)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def test_sse_01_every_event_matches_its_schema(chat_client):
    client, _ = chat_client(base_script(**ANSWER))
    login(client)
    for event, data in stream(client, button_id="pm_spend_by_vendor"):
        EVENT_MODELS[event].model_validate(data)


def test_sse_02_event_order_for_a_button(chat_client):
    client, _ = chat_client(base_script(**ANSWER))
    login(client)
    order = [e for e, _ in stream(client, button_id="pm_spend_by_vendor")]
    assert order[0] == "conversation" and order[-1] == "done"
    assert order.index("sql") < order.index("rows") < order.index("chart")
    assert order.index("rows") < order.index("token")


def test_sse_03_tokens_only_after_rows(chat_client):
    client, _ = chat_client(base_script(**ANSWER))
    login(client)
    order = [e for e, _ in stream(client, button_id="pm_spend_by_vendor")]
    first_token = order.index("token")
    assert "rows" in order[:first_token]


def test_sse_04_failure_sends_error_with_reference(chat_client):
    def explode(system, user):
        raise RuntimeError("boom at db.internal")

    client, _ = chat_client(base_script(**{Task.ANSWER: explode}))
    login(client)
    events = stream(client, button_id="pm_spend_by_vendor")
    error = next(d for e, d in events if e == "error")
    assert error["reference"] and "db.internal" not in json.dumps(events)


def test_sse_06_rate_limit(chat_client):
    client, _ = chat_client(base_script(**{Task.CHAT_REPLY: lambda s, u: "Hello"}),
                            rate_limit_per_minute=2)
    login(client)
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 200
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 200
    third = client.post("/api/chat/stream", json={"message": "hi"})
    assert third.status_code == 429


def test_chat_needs_a_session(chat_client):
    client, _ = chat_client()
    assert client.post("/api/chat/stream", json={"message": "hi"}).status_code == 401


def test_invalid_body_is_422(chat_client):
    client, _ = chat_client()
    login(client)
    assert client.post("/api/chat/stream", json={}).status_code == 422
    assert client.post("/api/chat/stream", json={"message": "x" * 1001}).status_code == 422


def test_rbac_08_po_actions_from_other_roles_are_denied(chat_client):
    client, llm = chat_client()
    login(client, "owner@demo.local")
    events = stream(client, po_action={"type": "confirm", "idempotency_key": "k"})
    reply = "".join(d["text"] for e, d in events if e == "token")
    assert "Only the Procurement Manager" in reply
    assert llm.calls_for(Task.PO_EXTRACT) == []


def test_rbac_10_role_in_the_body_is_ignored(chat_client):
    client, _ = chat_client()
    login(client, "warehouse@demo.local")
    response = client.post("/api/chat/stream", json={
        "message": "Raise a PO for 10 relays", "role": "procurement_manager"})
    assert response.status_code == 422  # unknown fields are rejected outright


def test_history_routes(chat_client):
    client, _ = chat_client(base_script(**ANSWER))
    login(client)
    events = stream(client, button_id="pm_spend_by_vendor")
    conversation_id = events[0][1]["conversation_id"]
    message_id = events[-1][1]["message_id"]

    listed = client.get("/api/conversations").json()
    assert listed[0]["id"] == conversation_id and listed[0]["title"] == "Spend by vendor"

    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert [m["sender"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["payload"]["chart"]["type"] == "horizontal_bar"
    assert detail["open_po_draft"] is None

    assert client.post("/api/feedback", json={"message_id": message_id, "score": 1}
                       ).status_code == 204
    assert client.delete(f"/api/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404


def test_history_is_private(chat_client):
    client, _ = chat_client(base_script(**ANSWER))
    login(client)
    conversation_id = stream(client, button_id="pm_spend_by_vendor")[0][1]["conversation_id"]
    login(client, "owner@demo.local")
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert client.get("/api/conversations").json() == []
