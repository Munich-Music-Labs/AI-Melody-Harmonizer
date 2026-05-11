"""FastAPI app exposing the harmonizer to the React frontend."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.pipeline import harmonize_file, list_available_genres

logger = logging.getLogger("ai_melody_harmonizer.backend")

app = FastAPI(
    title="AI Melody Harmonizer",
    description="HTTP API for the React-based harmonizer UI.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/genres")
def get_genres() -> dict:
    """List genre names that currently have trained weights on disk."""
    return {"genres": list_available_genres()}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


_ALLOWED_SUFFIXES = {".mid", ".midi"}


@app.post("/api/harmonize")
async def harmonize(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    genre: str = Form(...),
) -> FileResponse:
    """Accept a MIDI upload + genre, run the harmonizer, return harmonized MIDI."""
    original_name = file.filename or "input.mid"
    suffix = Path(original_name).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Upload a .mid or .midi file.",
        )

    available = list_available_genres()
    if genre not in available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown genre '{genre}'. Available: {available or 'none (train weights first)'}."
            ),
        )

    work_dir = Path(tempfile.mkdtemp(prefix="harmonize_"))
    background_tasks.add_task(_safe_rmtree, work_dir)

    input_path = work_dir / Path(original_name).name
    try:
        with input_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    try:
        harmonized_path = harmonize_file(input_path, genre, work_dir)
    except NotImplementedError as exc:
        logger.warning("MIDI conversion not implemented: %s", exc)
        raise HTTPException(status_code=501, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Missing model artifact: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.exception("Harmonization failed")
        raise HTTPException(status_code=500, detail=f"Harmonization failed: {exc}")

    download_name = f"{Path(original_name).stem}_harmonized_{genre}.mid"
    return FileResponse(
        path=str(harmonized_path),
        media_type="audio/midi",
        filename=download_name,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


def _safe_rmtree(path: Path) -> None:
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        logger.exception("Failed to clean up temp dir %s", path)
