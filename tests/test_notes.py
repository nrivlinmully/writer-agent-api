from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from storage import AUDIO_DIR, NOTES

client = TestClient(app)

def setup_funtion():
    NOTES.clear()
    if AUDIO_DIR.exists():
        for f in AUDIO_DIR.iterdir():
            if f.is_file():
                f.unlink()

def _create_dummy_audio(tmp_path: Path, is_audio: bool, name: str = "test.mp3") -> Path:
    file_path = tmp_path / name

    if is_audio:
        file_path.write_bytes(b"fake audio date")
    else:
        file_path.write_text("This is not an audio file")
    return file_path

class FakeInfo:
    length = 1.23

class FakeMutagenFile:
    def __init__(self, path):
        self.info = FakeInfo()

def test_create_note_accepts_supported_audio(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, "audio/mpeg")}
        response = client.post("/notes", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == audio_file.name
    assert data["size_bytes"] > 0
    assert data["duration_sec"] >= 0.0

def test_create_note_rejects_unsupported_extensions(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, False, name="test.txt")

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, "audio/txt")}
        response = client.post("/notes", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Invalid file type, expected audio/*, or .mp3/.m4a/.wav extension"

def test_get_notes_and_filter(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, "audio/mpeg")}
        create_response = client.post("/notes", files=files)

    note = create_response.json()

    list_response = client.get("/notes")
    assert list_response.status_code == 200
    notes = list_response.json()
    assert any(n["id"] == note["id"] for n in notes)

    filtered_response = client.get("/notes", params={"min_duration": 9999})
    assert filtered_response.status_code == 200
    assert filtered_response.json() == []

def test_get_note_and_not_found(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, "audio/mpeg")}
        create_response = client.post("/notes", files=files)

    note_id = create_response.json()["id"]
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["id"] == note_id

    response_not_found = client.get("/notes/nonexistent")
    assert response_not_found.status_code == 404

def test_get_note_audio_and_not_found(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, "audio/mpeg")}
        create_response = client.post("/notes", files=files)

    note_id = create_response.json()["id"]
    response_audio = client.get(f"/notes/{note_id}/audio")
    assert response_audio.status_code == 200
    assert response_audio.headers["content-type"] == "audio/mpeg"

    for f in AUDIO_DIR.iterdir():
        if f.is_file():
            f.unlink()

    response_missing = client.get(f"/notes/{note_id}/audio")
    assert response_missing.status_code == 404