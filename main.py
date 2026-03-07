from fastapi import FastAPI

from routes.notes import router as notes_router

app = FastAPI()

app.include_router(notes_router)