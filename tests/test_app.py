"""Tests for the app API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Test client with a temp saved_passages file."""
    import config
    monkeypatch.setattr(config, "SAVED_PASSAGES_FILE", tmp_path / "saved.json")
    return TestClient(app)


# ── GET / ────────────────────────────────────────────────────────────────────

def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Passage" in resp.text


# ── GET /api/search ──────────────────────────────────────────────────────────

def test_search_requires_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 422


def test_search_returns_results(client):
    fake_results = [
        {"chunk_id": "test_0000", "book_title": "Test Book", "text": "Some passage.", "word_count": 2, "score": 0.9},
    ]
    with patch("app.main.search", return_value=fake_results):
        resp = client.get("/api/search?q=meaning+of+life")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["book_title"] == "Test Book"


def test_search_empty_query(client):
    resp = client.get("/api/search?q=")
    assert resp.status_code == 422


# ── POST /api/saved ──────────────────────────────────────────────────────────

def test_save_passage(client):
    resp = client.post("/api/saved", json={
        "chunk_id": "test_0000",
        "book_title": "Test Book",
        "text": "A saved passage.",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"

    # Verify it shows up in the list
    resp = client.get("/api/saved")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["chunk_id"] == "test_0000"


def test_save_duplicate(client):
    payload = {"chunk_id": "test_0000", "book_title": "Test Book", "text": "A passage."}
    client.post("/api/saved", json=payload)
    resp = client.post("/api/saved", json=payload)
    assert resp.json()["status"] == "already_saved"

    # Still only one entry
    assert len(client.get("/api/saved").json()) == 1


# ── DELETE /api/saved/{chunk_id} ─────────────────────────────────────────────

def test_unsave_passage(client):
    client.post("/api/saved", json={
        "chunk_id": "test_0000",
        "book_title": "Test Book",
        "text": "A passage.",
    })
    resp = client.delete("/api/saved/test_0000")
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"
    assert len(client.get("/api/saved").json()) == 0


def test_unsave_nonexistent(client):
    resp = client.delete("/api/saved/doesnt_exist")
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"


# ── GET /api/saved (empty) ───────────────────────────────────────────────────

def test_saved_empty_by_default(client):
    resp = client.get("/api/saved")
    assert resp.status_code == 200
    assert resp.json() == []
