from app.services.file_manager import create_paper_folder


def test_create_paper_folder(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.file_manager.BASE_STORAGE", tmp_path)
    folder = create_paper_folder("123")
    assert folder.exists()
    assert folder.name == "paper_123"
