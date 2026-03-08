from datetime import datetime

from pydantic import BaseModel


class Note(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    duration_sec: float
    created_at: datetime