from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_full_pipeline(sample_pdf):
    with open(sample_pdf, "rb") as f:
        resp = client.post(
            "/upload/pdf", files={"file": ("paper.pdf", f, "application/pdf")}
        )

    assert resp.status_code == 200
    data = resp.json()
    paper_id = data["paper_id"]
    assert "summary" in data

    resp2 = client.get(f"/summary/{paper_id}")
    assert resp2.status_code == 200

    resp3 = client.post(
        "/chat", json={"paper_id": paper_id, "query": "What methodology did they use?"}
    )

    assert resp3.status_code == 200
    answer = resp3.json()["answer"].lower()

    assert "cnn" in answer or "method" in answer or "mock" in answer
