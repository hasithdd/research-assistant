import pytest
from reportlab.pdfgen import canvas

from backend.tests.mocks import mock_chatcompletion_create


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "sample.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 800, "ABSTRACT This paper studies X.")
    c.drawString(100, 780, "INTRODUCTION The problem is Y.")
    c.drawString(100, 760, "METHODOLOGY We do Z.")
    c.drawString(100, 740, "RESULTS Accuracy is 90%.")
    c.drawString(100, 720, "CONCLUSION Final remarks.")
    c.save()
    return path


@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    monkeypatch.setattr("openai.ChatCompletion.create", mock_chatcompletion_create)
