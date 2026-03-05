from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from mutagen import File as MutagenFile
from pydantic import BaseModel
from typing import Annotated
from pathlib import Path
from uuid import uuid4

app = FastAPI()

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

class Note(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    duration_sec: float

NOTES: dict[str, Note] = {}

@app.post("/notes", response_model=Note)
async def create_note(file: UploadFile = File(...)):
    if not looks_like_audio(file):
        raise HTTPException(status_code=400, detail="Invalid file type, expected audio/*")

    out_path = AUDIO_DIR / Path(file.filename)

    size = 0
    with out_path.open("wb") as f:
        while chunk := await file.read(1024*1024):
            size += len(chunk)
            f.write(chunk)

    audio = MutagenFile(out_path)
    duration_sec = float(audio.info.length) if audio and audio.info else 0.0

    note = Note(
        id=str(uuid4()),
        filename=out_path.name,
        content_type=file.content_type,
        size_bytes=size,
        duration_sec=duration_sec
    )

    NOTES[note.id] = note
    return note

@app.get("/notes", response_model=list[Note])
async def get_notes(min_duration: Annotated[float | None, Query(ge=0)] = None):
    notes = list(NOTES.values())
    if min_duration is not None:
        notes = [n for n in notes if n.duration_sec >= min_duration]
    return notes

@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: str):
    return get_note_or_404(note_id)

@app.get("/notes/{note_id}/audio", response_class=FileResponse)
async def get_note_audio(note_id: str):
    note = get_note_or_404(note_id)

    file_path = AUDIO_DIR / note.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=file_path,
        media_type=note.content_type,
        filename=note.filename,
    )

def get_note_or_404(note_id: str) -> Note:
    note = NOTES.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

def looks_like_audio(file: UploadFile) -> bool:
    if file.content_type.startswith("audio/"):
        return True
    suffix = Path(file.filename).suffix.lower()
    return suffix in (".mp3", ".m4a", ".wav")