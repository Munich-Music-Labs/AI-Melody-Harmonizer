"""Pre-processing: convert an uploaded MIDI file into MusicXML.

The harmonizer pipeline (`loader._process_single_file`, `loader.melody_reader`)
expects a MusicXML where:
- ``score.parts[0]`` is the melody.
- A ``key.Key`` / ``key.KeySignature`` is present so the loader can extract
  the number of sharps for each note.
- A ``meter.TimeSignature`` is present so ``element.beatStrength`` is
  meaningful (the loader uses ``beatStrength * 4`` as the beat token).

This module does *not* re-quantize the score. ``loader.quant_score`` already
snaps offsets / durations to a 16th-note grid before harmonization, so doing
it here would just be redundant work.
"""

from pathlib import Path

from music21 import converter
from music21 import key as m21key
from music21 import meter, note, stream


def _legato_melody(melody_part: stream.Part) -> None:
    """Stretch each Note's duration to the next note's onset and remove
    explicit Rests in between, in-place.

    Music21's MIDI parser splits each played note into a short audible slice
    followed by an explicit Rest covering the rest of the gap to the next
    onset. The harmonizer's loader was trained on lead-sheet MusicXML where
    notes sustain across all of their 16th-note slots, so leaving the
    fragmented MIDI representation in place causes the encoded melody to look
    mostly silent and the model collapses to predicting 'R' (rest).
    """
    notes_with_offset = []
    for n in list(melody_part.recurse().getElementsByClass(note.Note)):
        try:
            global_offset = float(n.getOffsetInHierarchy(melody_part))
        except Exception:
            global_offset = float(n.offset)
        notes_with_offset.append((global_offset, n))
    notes_with_offset.sort(key=lambda pair: pair[0])

    melody_end = float(melody_part.highestTime)
    for i, (off, n) in enumerate(notes_with_offset):
        next_off = notes_with_offset[i + 1][0] if i + 1 < len(notes_with_offset) else melody_end
        new_ql = max(0.25, float(next_off) - float(off))
        try:
            n.quarterLength = new_ql
        except Exception:
            pass

    for r in list(melody_part.recurse().getElementsByClass(note.Rest)):
        try:
            site = r.activeSite
            if site is not None:
                site.remove(r)
        except Exception:
            pass


def midi_to_musicxml(midi_path: Path, out_dir: Path) -> Path:
    """Convert a MIDI file at ``midi_path`` to a MusicXML file in ``out_dir``.

    Returns the path to the produced ``.musicxml`` file.

    Assumptions
    -----------
    The melody lives on the first track / part of the MIDI file. This matches
    the convention used by most lead-sheet exporters and mirrors what the
    existing loader already does (``score.parts[0]``).
    """
    midi_path = Path(midi_path)
    out_dir = Path(out_dir)

    score = converter.parse(str(midi_path), quantizePost=True)

    melody_part = score.parts[0] if getattr(score, "parts", None) and len(score.parts) > 0 else score

    _legato_melody(melody_part)

    if not melody_part.recurse().getElementsByClass(m21key.KeySignature):
        try:
            analyzed = melody_part.analyze("key")
            melody_part.insert(0, analyzed)
        except Exception:
            melody_part.insert(0, m21key.KeySignature(0))

    if not melody_part.recurse().getElementsByClass(meter.TimeSignature):
        melody_part.insert(0, meter.TimeSignature("4/4"))

    out_score = stream.Score()
    out_score.insert(0, melody_part)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{midi_path.stem}.musicxml"
    out_score.write("musicxml", fp=str(out_path))
    return out_path
