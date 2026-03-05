from pathlib import Path

from fastapi import HTTPException, UploadFile

from models import Note

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

NOTES: dict[str, Note] = {}

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav"}

def get_note_or_404(note_id: str) -> Note:
    note = NOTES.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

def is_supported_audio(file: UploadFile) -> bool:
    suffix = Path(file.filename).suffix.lower()
    return suffix in ALLOWED_AUDIO_EXTENSIONS
