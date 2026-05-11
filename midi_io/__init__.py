"""MIDI <-> MusicXML conversion helpers used by the web UI backend.

These functions adapt user-uploaded MIDI files into the MusicXML format that
``loader.convert_files`` / ``melody_reader`` expect, and convert the
harmonized MusicXML output back into a MIDI file with a realized accompaniment
track for download.
"""

from midi_io.midi_to_musicxml import midi_to_musicxml
from midi_io.musicxml_to_midi import musicxml_to_midi

__all__ = ["midi_to_musicxml", "musicxml_to_midi"]
