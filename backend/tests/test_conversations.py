from unittest.mock import patch


def _register(client, email="c@d.com", password="pwpwpwpw"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    return r.json()["token"]


def test_create_conversation(client):
    token = _register(client)
    r = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "test", "documentIds": []},
    )
    assert r.status_code == 201
    assert r.json()["title"] == "test"


def test_list_conversations(client):
    token = _register(client, email="c2@d.com")
    client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    r = client.get("/api/conversations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["totalElements"] == 1


def test_delete_conversation(client):
    token = _register(client, email="c3@d.com")
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]
    r = client.delete(f"/api/conversations/{cid}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204


def test_send_message_and_get_response(client):
    token = _register(client, email="c4@d.com")
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]

    with patch("app.conversations.service.run_agent") as mock_agent:
        mock_agent.return_value = {
            "answer": "mock answer",
            "sources": [],
            "iterations_used": 1,
        }
        r = client.post(
            f"/api/conversations/{cid}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hello", "documentIds": []},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "ASSISTANT"
    assert body["content"] == "mock answer"


def test_list_messages_cursor_pagination(client):
    token = _register(client, email="c5@d.com")
    r = client.post("/api/conversations", headers={"Authorization": f"Bearer {token}"}, json={})
    cid = r.json()["id"]

    with patch("app.conversations.service.run_agent") as mock_agent:
        mock_agent.return_value = {"answer": "a", "sources": [], "iterations_used": 1}
        for i in range(3):
            client.post(
                f"/api/conversations/{cid}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": f"q{i}", "documentIds": []},
            )

    r = client.get(f"/api/conversations/{cid}/messages?size=10", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["content"]) == 6  # 3 user + 3 assistant
    assert body["hasMore"] is False
