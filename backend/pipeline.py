"""End-to-end harmonization pipeline used by the FastAPI backend.

Reuses the existing CLI logic in ``harmonizer.py`` and ``loader.py`` so the
web UI and the CLI stay in sync. Models and chord vocabularies are cached
per-genre in module-level dicts to avoid reloading TensorFlow on every
request.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Dict, List, Tuple

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from config import (
    DROPOUT,
    NUM_LAYERS,
    RNN_SIZE,
    SEGMENT_LENGTH,
    WEIGHTS_ROOT,
    BASELINE_GENRE,
    get_chord_types_path,
    get_weights_path,
    normalize_genre,
)
from harmonizer import export_music, generate_chord
from loader import convert_files, load_chord_types
from midi_io import midi_to_musicxml, musicxml_to_midi
from model import build_model

_model_cache: Dict[str, Tuple[object, list]] = {}
_model_cache_lock = Lock()


def list_available_genres() -> List[str]:
    """Return genre names that have trained weights on disk.

    Always reports ``baseline`` first if its weights exist, followed by every
    sub-folder under ``weights/genres/<name>/`` that contains ``weights.keras``.
    """
    genres: List[str] = []

    baseline_path = Path(get_weights_path(BASELINE_GENRE))
    if baseline_path.exists():
        genres.append(BASELINE_GENRE)

    genres_root = Path(WEIGHTS_ROOT) / "genres"
    if genres_root.is_dir():
        for entry in sorted(genres_root.iterdir()):
            if not entry.is_dir():
                continue
            if (entry / "weights.keras").exists():
                genres.append(entry.name)

    return genres


def _load_model_for_genre(genre: str) -> Tuple[object, list]:
    """Load and cache (model, chord_types) for ``genre``."""
    genre = normalize_genre(genre)

    with _model_cache_lock:
        if genre in _model_cache:
            return _model_cache[genre]

        weights_path = get_weights_path(genre)
        chord_types_path = get_chord_types_path(genre)

        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Missing weights for genre '{genre}' at {weights_path}. "
                "Train or fine-tune this genre first."
            )

        chord_types = load_chord_types(chord_types_path)
        if not chord_types:
            raise FileNotFoundError(
                f"Missing shared chord vocabulary at {chord_types_path}. "
                "Run loader with --build-global-vocab first."
            )

        model = build_model(
            SEGMENT_LENGTH,
            RNN_SIZE,
            NUM_LAYERS,
            DROPOUT,
            weights_path=weights_path,
            chord_types_path=chord_types_path,
            training=False,
        )

        _model_cache[genre] = (model, chord_types)
        return model, chord_types


def harmonize_file(input_midi: Path, genre: str, work_dir: Path) -> Path:
    """Harmonize ``input_midi`` with the given ``genre`` weights.

    Writes intermediate and output files into ``work_dir`` (typically a
    request-scoped temp directory) and returns the path to the harmonized
    ``.mid`` file. The original ``inputs/`` and ``outputs/`` folders are not
    touched.
    """
    input_midi = Path(input_midi)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    musicxml_in = midi_to_musicxml(input_midi, work_dir)

    model, chord_types = _load_model_for_genre(genre)

    data = convert_files([str(musicxml_in)], fromDataset=False)
    if not data:
        raise RuntimeError("Failed to parse the uploaded MIDI as a melody.")

    md, bd, kd, score_obj, fname = data[0]
    chords = generate_chord(model, md, bd, kd, chord_types=chord_types)

    export_music(
        score_obj,
        bd,
        chords,
        fname,
        chord_types=chord_types,
        outputs_path=str(work_dir),
    )

    harmonized_musicxml = work_dir / f"{musicxml_in.stem}.mxl"
    if not harmonized_musicxml.exists():
        raise RuntimeError(
            f"Harmonized MusicXML not found at {harmonized_musicxml}. "
            "Did export_music change its output convention?"
        )

    harmonized_midi = musicxml_to_midi(harmonized_musicxml, work_dir)
    return harmonized_midi
