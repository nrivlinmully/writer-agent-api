from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from mutagen import File as MutagenFile
from typing import Annotated
from pathlib import Path
from uuid import uuid4

from models import Note
from storage import AUDIO_DIR, NOTES, is_supported_audio, get_note_or_404

router = APIRouter()

@router.post("/notes", response_model=Note)
async def create_note(file: UploadFile = File(...)):
    if not is_supported_audio(file):
        raise HTTPException(status_code=400, detail="Invalid file type, expected audio/*, or .mp3/.m4a/.wav extension")

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
        duration_sec=duration_sec,
        created_at=datetime.now(timezone.utc),
    )

    NOTES[note.id] = note
    return note

@router.get("/notes", response_model=list[Note])
async def get_notes(min_duration: Annotated[float | None, Query(ge=0)] = None,
                    created_after: Annotated[datetime | None, Query()] = None,
                    created_before: Annotated[datetime | None, Query()] = None
):
    notes = list(NOTES.values())

    if min_duration is not None:
        notes = [n for n in notes if n.duration_sec >= min_duration]

    if created_after is not None:
        notes = [n for n in notes if n.created_at >= created_after]

    if created_before is not None:
        notes = [n for n in notes if n.created_at <= created_before]

    return notes

@router.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: str):
    return get_note_or_404(note_id)

@router.get("/notes/{note_id}/audio", response_class=FileResponse)
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