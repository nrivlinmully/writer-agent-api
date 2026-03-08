from datetime import datetime, timedelta
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

    response = upload_note_audio_for_test(audio_file)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == audio_file.name
    assert data["size_bytes"] > 0
    assert data["duration_sec"] >= 0.0
    assert data["created_at"]


def test_create_note_rejects_unsupported_extensions(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, False, name="test.txt")

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    response = upload_note_audio_for_test(audio_file, content_type="text/plain")

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Invalid file type, expected audio/*, or .mp3/.m4a/.wav extension"

def test_get_notes_and_filters(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    create_response = upload_note_audio_for_test(audio_file)

    note = create_response.json()

    list_response = client.get("/notes")
    assert list_response.status_code == 200
    notes = list_response.json()
    assert any(n["id"] == note["id"] for n in notes)

    min_duration_response = client.get("/notes", params={"min_duration": 9999})
    assert min_duration_response.status_code == 200
    assert min_duration_response.json() == []

    create_at = datetime.fromisoformat(note["created_at"].replace("Z", "+00:00"))

    after = (create_at + timedelta(seconds=1)).isoformat()
    created_after_response = client.get("/notes", params={"created_after": after})
    assert created_after_response.status_code == 200
    assert all(n["id"] != note["id"] for n in created_after_response.json())

    before = (create_at + timedelta(seconds=1)).isoformat()
    created_before_response = client.get("/notes", params={"created_before": before})
    assert created_before_response.status_code == 200
    assert any(n["id"] == note["id"] for n in created_before_response.json())

def test_get_note_and_not_found(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    create_response = upload_note_audio_for_test(audio_file)

    note_id = create_response.json()["id"]
    response = client.get(f"/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["id"] == note_id

    response_not_found = client.get("/notes/nonexistent")
    assert response_not_found.status_code == 404

def test_get_note_audio_and_not_found(tmp_path, monkeypatch):
    audio_file = _create_dummy_audio(tmp_path, True)

    monkeypatch.setattr("routes.notes.MutagenFile", FakeMutagenFile)

    create_response = upload_note_audio_for_test(audio_file)

    note_id = create_response.json()["id"]
    response_audio = client.get(f"/notes/{note_id}/audio")
    assert response_audio.status_code == 200
    assert response_audio.headers["content-type"] == "audio/mpeg"

    for f in AUDIO_DIR.iterdir():
        if f.is_file():
            f.unlink()

    response_missing = client.get(f"/notes/{note_id}/audio")
    assert response_missing.status_code == 404

def upload_note_audio_for_test(audio_file, content_type="audio/mpeg"):
    with audio_file.open("rb") as f:
        files = {"file": (audio_file.name, f, content_type)}
        response = client.post("/notes", files=files)
    return response