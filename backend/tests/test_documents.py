import io
import pytest
from unittest.mock import patch


def _register(client, email="d@e.com", password="pwpwpwpw"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    return r.json()["token"]


def test_upload_document(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client)
    pdf_bytes = b"%PDF-1.4 minimal"

    with patch("app.documents.service.ingest_document_task") as mock_task:
        mock_task.delay.return_value = None
        r = client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "test.pdf"
    assert body["status"] == "PROCESSING"
    assert "id" in body


def test_upload_rejects_non_pdf(client):
    token = _register(client, email="d2@e.com")
    r = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_list_documents(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client, email="d3@e.com")
    pdf_bytes = b"%PDF-1.4 minimal"
    with patch("app.documents.service.ingest_document_task"):
        client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    r = client.get("/api/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["totalElements"] == 1
    assert body["content"][0]["filename"] == "a.pdf"


def test_delete_document(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.documents.service.settings.uploads_dir", str(tmp_path))
    token = _register(client, email="d4@e.com")
    pdf_bytes = b"%PDF-1.4 minimal"
    with patch("app.documents.service.ingest_document_task"):
        r = client.post(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("b.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
    doc_id = r.json()["id"]
    with patch("app.documents.service.delete_document_from_chroma"):
        r = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
