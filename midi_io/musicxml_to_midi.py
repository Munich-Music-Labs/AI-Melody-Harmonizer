"""Post-processing: convert harmonized MusicXML into a MIDI file.

The harmonizer's ``export_music`` writes a Score that contains the original
melody plus ``harmony.ChordSymbol`` elements at the right offsets. MIDI
players don't render ``ChordSymbol`` as audible notes by default, so this
module realizes each chord symbol as a block chord on a second piano part
and writes the combined Score to MIDI.
"""

from pathlib import Path

from music21 import chord, converter, harmony, instrument, meter, note, stream


def musicxml_to_midi(musicxml_path: Path, out_dir: Path) -> Path:
    """Convert a harmonized MusicXML file at ``musicxml_path`` to a MIDI file
    in ``out_dir``. Returns the path to the produced ``.mid`` file.

    Each ``harmony.ChordSymbol`` is realized as a block chord held until the
    next chord change (or the end of the piece), voiced around octave 3 so it
    sits below a typical melody.
    """
    musicxml_path = Path(musicxml_path)
    out_dir = Path(out_dir)

    score = converter.parse(str(musicxml_path))
    melody_part = score.parts[0] if getattr(score, "parts", None) and len(score.parts) > 0 else score

    # Collect (offset, ChordSymbol) pairs ordered by global offset.
    chord_symbols = []
    for cs in score.recurse().getElementsByClass(harmony.ChordSymbol):
        try:
            offset = cs.getOffsetInHierarchy(score)
        except Exception:
            offset = float(cs.offset)
        chord_symbols.append((float(offset), cs))
    chord_symbols.sort(key=lambda pair: pair[0])

    total_length = float(melody_part.highestTime)
    if total_length <= 0 and chord_symbols:
        total_length = chord_symbols[-1][0] + 4.0

    accompaniment = stream.Part()
    accompaniment.insert(0, instrument.Piano())

    for i, (offset, cs) in enumerate(chord_symbols):
        next_offset = chord_symbols[i + 1][0] if i + 1 < len(chord_symbols) else total_length
        duration = max(0.25, float(next_offset) - float(offset))

        pitches = list(cs.pitches)
        if not pitches:
            accompaniment.insert(offset, note.Rest(quarterLength=duration))
            continue

        root = pitches[0]
        shift_octaves = 3 - root.octave
        if shift_octaves != 0:
            voiced = [p.transpose(12 * shift_octaves) for p in pitches]
        else:
            voiced = pitches

        ch = chord.Chord(voiced, quarterLength=duration)
        accompaniment.insert(offset, ch)

    # music21's MIDI writer calls Part.expandRepeats() on every part of the
    # Score, and that raises on a measureless Part regardless of whether any
    # repeats actually exist. Wrap the offset-based accompaniment in measures
    # using the melody's time signature so bars line up with the melody.
    ts_src = melody_part.recurse().getElementsByClass(meter.TimeSignature).first()
    accompaniment.insert(
        0,
        meter.TimeSignature(ts_src.ratioString) if ts_src is not None else meter.TimeSignature("4/4"),
    )
    accompaniment.makeMeasures(inPlace=True)

    out_score = stream.Score()
    out_score.insert(0, melody_part)
    out_score.insert(0, accompaniment)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{musicxml_path.stem}.mid"
    out_score.write("midi", fp=str(out_path))
    return out_path
