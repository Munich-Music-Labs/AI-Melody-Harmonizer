import os
import argparse
import pickle
import numpy as np
from copy import deepcopy
from tqdm import trange
from music21 import *
from config import *

def quant_score(score):
    
    for element in score.flat:
        onset = np.ceil(element.offset/0.25)*0.25

        if isinstance(element, note.Note) or isinstance(element, note.Rest) or isinstance(element, chord.Chord):
            offset = np.ceil((element.offset+element.quarterLength)/0.25)*0.25
            element.quarterLength = offset - onset

        element.offset = onset

    return score


def get_filenames(input_dir, extensions=EXTENSION):
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    ext_set = {ext.lower() for ext in extensions} if extensions is not None else None

    # Use list comprehension for better performance
    filenames = [
        os.path.join(dirpath, this_file)
        for dirpath, dirlist, filelist in os.walk(input_dir)
        for this_file in filelist
        if ext_set is None or os.path.splitext(this_file)[-1].lower() in ext_set
    ]
    return filenames


def melody_reader(score):
    # Pre-calculate total length for efficient memory allocation
    total_length = 0
    elements_data = []
    sharps = 0
    chord_token = 'R'
    
    for element in score.flat:
        if isinstance(element, note.Note):
            token = element.pitch.midi
            duration = int(element.quarterLength*4)
            beat = int(element.beatStrength*4)
            if duration > 0:  # Skip zero-length notes
                elements_data.append((token, beat, sharps, chord_token, duration))
                total_length += duration
            
        elif isinstance(element, note.Rest):
            token = 0
            duration = int(element.quarterLength*4)
            beat = int(element.beatStrength*4)
            if duration > 0:  # Skip zero-length rests
                elements_data.append((token, beat, sharps, chord_token, duration))
                total_length += duration
            
        elif isinstance(element, chord.Chord) and not isinstance(element, harmony.ChordSymbol):
            notes = [n.pitch.midi for n in element.notes]
            if notes:  # Ensure there are notes
                token = max(notes)  # max() is faster than sort() + [-1]
                duration = int(element.quarterLength*4)
                beat = int(element.beatStrength*4)
                if duration > 0:  # Skip zero-length chords
                    elements_data.append((token, beat, sharps, chord_token, duration))
                    total_length += duration
            
        elif isinstance(element, harmony.ChordSymbol):
            chord_token = element.figure
            
        elif isinstance(element, key.Key) or isinstance(element, key.KeySignature):
            sharps = element.sharps+8
    
    # Preallocate arrays with appropriate dtypes
    melody_txt = np.zeros(total_length, dtype=np.uint8)
    beat_txt = np.zeros(total_length, dtype=np.uint8)
    key_txt = np.zeros(total_length, dtype=np.uint8)
    chord_txt = []
    
    # Fill arrays efficiently
    idx = 0
    for token_val, beat_val, key_val, chord_val, duration in elements_data:
        melody_txt[idx:idx+duration] = token_val
        beat_txt[idx:idx+duration] = beat_val
        key_txt[idx:idx+duration] = key_val
        chord_txt.extend([chord_val] * duration)
        idx += duration
    
    # Convert to lists for compatibility with existing code
    return melody_txt.tolist(), beat_txt.tolist(), key_txt.tolist(), chord_txt


def normalize_chord_types(chord_types):
    unique_ordered = list(dict.fromkeys(chord_types))
    if "R" in unique_ordered:
        unique_ordered.remove("R")
    return ["R"] + unique_ordered


def load_chord_types(chord_types_path):
    if not os.path.exists(chord_types_path):
        return None
    with open(chord_types_path, "rb") as filepath:
        return pickle.load(filepath)


def convert_files(
    filenames,
    fromDataset=True,
    corpus_path=CORPUS_PATH,
    chord_types_path=CHORD_TYPES_PATH,
    shared_chord_types=None,
    unknown_chord_policy="skip_song",
):

    print('\nConverting %d files...' %(len(filenames)))
    failed_list = []
    data_corpus = []
    observed_chord_types = []
    observed_chord_set = set()
    shared_chord_set = set(shared_chord_types) if shared_chord_types is not None else None

    for filename_idx in trange(len(filenames)):

        # Read this music file
        filename = filenames[filename_idx]
        
        try:
            
            score = converter.parse(filename)
            score = score.parts[0]
            if not fromDataset:
                original_score = deepcopy(score)
            song_data = []
            melody_data = []
            beat_data = []
            key_data = []

            score = quant_score(score)
            melody_txt, beat_txt, key_txt, chord_txt = melody_reader(score)

            if fromDataset:
                if shared_chord_set is not None:
                    unknown_chords = sorted({ch for ch in chord_txt if ch not in shared_chord_set})
                    if unknown_chords:
                        if unknown_chord_policy == "map_to_R":
                            chord_txt = [ch if ch in shared_chord_set else "R" for ch in chord_txt]
                        else:
                            failed_list.append((filename, f"unknown chord types: {unknown_chords[:10]}"))
                            continue

                if len(melody_txt)==len(beat_txt) and len(beat_txt)==len(key_txt) and len(key_txt)==len(chord_txt):
                    song_data.append((melody_txt, beat_txt, key_txt, chord_txt))
                    if shared_chord_set is None:
                        for chord_type in chord_txt:
                            if chord_type not in observed_chord_set:
                                observed_chord_set.add(chord_type)
                                observed_chord_types.append(chord_type)
                
                else:
                    failed_list.append((filename, 'length mismatch'))
                    song_data = []
                    continue

            else:
                if len(melody_txt)!=len(beat_txt) or len(melody_txt)!=len(key_txt):
                    min_len = min(len(melody_txt), len(beat_txt))
                    melody_txt = melody_txt[:min_len]
                    beat_txt = beat_txt[:min_len]
                    key_txt = key_txt[:min_len]
                    
                melody_data.append(melody_txt)
                beat_data.append(beat_txt)
                key_data.append(key_txt)
            
            if not fromDataset:
                data_corpus.append((melody_data, beat_data, key_data, original_score, filename))
            
            elif len(song_data)>0:
                data_corpus.append(song_data)

        except Exception as e:
            failed_list.append((filename, e))

    print('Successfully converted %d files.' %(len(filenames)-len(failed_list)))
    if len(failed_list)>0:
        print('Failed numbers: '+str(len(failed_list)))
        print('Failed to process: \n')
        for failed_file in failed_list:
            print(failed_file)

    if fromDataset:
        if shared_chord_types is None:
            chord_types = normalize_chord_types(observed_chord_types) if observed_chord_types else ["R"]
        else:
            chord_types = normalize_chord_types(shared_chord_types)

        print(f"Found {len(chord_types)} unique chord types")

        chord_dir = os.path.dirname(chord_types_path)
        corpus_dir = os.path.dirname(corpus_path)
        if chord_dir:
            os.makedirs(chord_dir, exist_ok=True)
        if corpus_dir:
            os.makedirs(corpus_dir, exist_ok=True)

        with open(chord_types_path, "wb") as filepath:
            pickle.dump(chord_types, filepath)

        with open(corpus_path, "wb") as filepath:
            pickle.dump(data_corpus, filepath)
    
    else:
        return data_corpus


def _cleanup_targets(corpus_path, chord_types_path=None):
    for path in [corpus_path, chord_types_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"  - Deleted {path}")
            except OSError as e:
                print(f"  - Error deleting {path}: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build corpus files for baseline or genre datasets.")
    parser.add_argument("--genre", default=DEFAULT_GENRE, help="Genre name. Use baseline for the base dataset.")
    parser.add_argument(
        "--dataset-dir",
        default=None,
        help="Override genre dataset root directory. Loader reads score sheets from <dataset-dir>/scoresheets.",
    )
    parser.add_argument("--corpus-path", default=None, help="Override output corpus path.")
    parser.add_argument(
        "--build-global-vocab",
        action="store_true",
        help="Rebuild the shared global chord vocabulary from this dataset.",
    )
    parser.add_argument(
        "--use-global-vocab",
        action="store_true",
        help="Use the shared global chord vocabulary and filter unknown chords.",
    )
    parser.add_argument(
        "--unknown-chord-policy",
        choices=["skip_song", "map_to_R"],
        default="skip_song",
        help="How to handle chords not found in the global vocabulary.",
    )
    args = parser.parse_args()

    if args.build_global_vocab and args.use_global_vocab:
        raise ValueError("Choose either --build-global-vocab or --use-global-vocab, not both.")

    genre = normalize_genre(args.genre)
    scoresheets_dir = (
        os.path.join(args.dataset_dir, "scoresheets")
        if args.dataset_dir
        else get_scoresheets_dir(genre)
    )
    corpus_path = args.corpus_path or get_corpus_path(genre)
    chord_types_path = get_chord_types_path(genre)

    if not args.build_global_vocab and not args.use_global_vocab:
        args.use_global_vocab = os.path.exists(chord_types_path)
        args.build_global_vocab = not args.use_global_vocab

    print("[LOADER] Cleaning up old corpus artifacts...")
    _cleanup_targets(corpus_path, chord_types_path if args.build_global_vocab else None)

    shared_chord_types = None
    if args.use_global_vocab:
        shared_chord_types = load_chord_types(chord_types_path)
        if not shared_chord_types:
            raise FileNotFoundError(
                f"Global chord vocabulary not found at {chord_types_path}. Run with --build-global-vocab first."
            )

    if not os.path.isdir(scoresheets_dir):
        raise FileNotFoundError(
            f"Missing score sheets directory: {scoresheets_dir}. Place MusicXML files in this folder first."
        )

    filenames = get_filenames(input_dir=scoresheets_dir)
    if not filenames:
        raise ValueError(f"No score sheets found in {scoresheets_dir}.")

    convert_files(
        filenames,
        fromDataset=True,
        corpus_path=corpus_path,
        chord_types_path=chord_types_path,
        shared_chord_types=shared_chord_types,
        unknown_chord_policy=args.unknown_chord_policy,
    )