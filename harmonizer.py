import os
import warnings
import argparse
import numpy as np
from config import *
from music21 import *
from tqdm import trange
from copy import deepcopy
from model import build_model
from samplings import gamma_sampling
from loader import get_filenames, convert_files, load_chord_types

# force CPU-only and suppress TF warnings
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings("ignore")

# Step-by-step inference (autoregressive)
# We cannot batch like before because each chord depends on the previous generated chord.
INFER_BATCH_SIZE = 1 

def generate_chord(chord_model, melody_data, beat_data, key_data,
                   chord_types,
                   segment_length=SEGMENT_LENGTH, rhythm_gamma=RHYTHM_DENSITY,
                   chord_per_bar=CHORD_PER_BAR):

    chord_data_list = []

    for song_idx, song_melody in enumerate(melody_data):
        # Prepare inputs (Integer integers, not One-Hot)
        padded_melody = segment_length*[0] + song_melody + segment_length*[0]
        padded_beat   = segment_length*[0] + beat_data[song_idx]   + segment_length*[0]
        padded_key    = segment_length*[0] + key_data[song_idx]    + segment_length*[0]
        
        # Output buffer (start with zeros/rests)
        # Assuming 0 is 'R' or the padding index. 
        # Check chord_types order ideally, but usually 0 is generic.
        song_chord    = segment_length * [0] 

        n_steps = len(padded_melody) - 2*segment_length
        
        # Iterate one step at a time
        for t in trange(segment_length, len(padded_melody)-segment_length,
                        desc=f"Song {song_idx+1} [{n_steps} steps]"):
            
            # Context Indices
            left_start, left_end = t-segment_length, t
            right_start, right_end = t, t+segment_length
            
            # --- PREPARE INPUTS (Indices) ---
            # 1. Melody
            p_mel_l = np.array([padded_melody[left_start:left_end]], dtype=np.uint8)
            p_mel_r = np.array([padded_melody[right_start:right_end][::-1]], dtype=np.uint8) # Reverse future
            
            # 2. Beat
            p_beat_l = np.array([padded_beat[left_start:left_end]], dtype=np.uint8)
            p_beat_r = np.array([padded_beat[right_start:right_end][::-1]], dtype=np.uint8)
            
            # 3. Key
            p_key_l = np.array([padded_key[left_start:left_end]], dtype=np.uint8)
            p_key_r = np.array([padded_key[right_start:right_end][::-1]], dtype=np.uint8)
            
            # 4. Chord History
            # IMPORTANT: this is where autoregressive behavior happens.
            # We take the last generated 'segment_length' chords.
            hist_chord = song_chord[-segment_length:]
            p_chord_l = np.array([hist_chord], dtype=np.uint16)
            
            # --- MODEL PREDICION ---
            
            inputs = {
                "input_melody_left": p_mel_l,
                "input_melody_right": p_mel_r,
                "input_beat_left": p_beat_l,
                "input_beat_right": p_beat_r,
                "input_key_left": p_key_l,
                "input_key_right": p_key_r,
                "input_chord_left": p_chord_l
            }
            
            pred_probs = chord_model.predict(inputs, verbose=0)[0] # Shape (num_chords,)

            # --- SAMPLING STRATEGY ---
            prev_chord_idx = song_chord[-1]
            current_beat = padded_beat[t]
            
            if chord_per_bar:
                # Force change only on downbeat (beat 4 in some encoding? or 1?)
                # Assuming standard music21: beat strength 1.0 -> 4 int conversion
                gamma = 1 if current_beat == 4 and prev_chord_idx != song_chord[-1] else 0
            else:
                gamma = rhythm_gamma

            # Applying sampling constraints
            tuned_probs = gamma_sampling(pred_probs, [[prev_chord_idx]], [gamma], return_probs=True)
            
            # Greedy choice (argmax) or probabilistic sample?
            # Usually argmax for stability unless temperature is needed.
            chosen_chord_idx = np.argmax(tuned_probs)
            
            song_chord.append(chosen_chord_idx)

        chord_data_list.append(song_chord[segment_length:])

    return chord_data_list

def watermark(score, filename, water_mark=WATER_MARK):
    if water_mark:
        score.metadata = metadata.Metadata()
        score.metadata.title = filename
        score.metadata.composer = 'harmonized by AutoHarmonizer'
    return score

def export_music(score, beat_data, chord_data, filename,
                 chord_types,
                 repeat_chord=REPEAT_CHORD, outputs_path=OUTPUTS_PATH,
                 water_mark=WATER_MARK):

    harmony_list = []
    offset = 0.0
    base = os.path.basename(filename)
    stem = '.'.join(base.split('.')[:-1])

    for idx, song_ch in enumerate(chord_data):
        # Convert indices back to chord names
        labels = [chord_types[int(c)].replace('N.C.', 'R').replace('bpedal', '-pedal') for c in song_ch]
        pre = None
        for t, lbl in enumerate(labels):
            if lbl != 'R' and (lbl != pre or (repeat_chord and beat_data[idx][t] == 4)):
                cs = harmony.ChordSymbol(lbl)
                cs.offset = offset
                harmony_list.append(cs)
            offset += 0.25
            pre = lbl

    # Build the output by deep-copying the original Part once (preserves clefs,
    # key/time signatures, instruments, repeat brackets, slurs, etc.) and then
    # inserting ChordSymbols into the right measure at the right local offset.
    # We deliberately do NOT rebuild measures via `Stream.elements = [...]`,
    # because that path resets every existing element's offset to 0.
    new_part = deepcopy(score)
    measures_in_part = list(new_part.getElementsByClass(stream.Measure))

    h_idx = 0
    for m_idx, new_m in enumerate(measures_in_part, start=1):
        m_start = float(new_m.offset)
        m_qlen = float(new_m.quarterLength) if new_m.quarterLength else float(new_m.highestTime)
        is_last = (m_idx == len(measures_in_part))
        m_end = m_start + m_qlen

        while h_idx < len(harmony_list) and (
            harmony_list[h_idx].offset < m_end
            or (is_last and harmony_list[h_idx].offset <= m_end)
        ):
            global_off = float(harmony_list[h_idx].offset)
            local_off = max(0.0, global_off - m_start)
            if m_qlen > 0 and local_off >= m_qlen:
                local_off = max(0.0, m_qlen - 0.25)
            new_m.insert(local_off, harmony_list[h_idx])
            h_idx += 1

    final_score = stream.Score()
    final_score.insert(0, new_part)

    if water_mark:
        final_score = watermark(final_score, stem)

    os.makedirs(outputs_path, exist_ok=True)
    output_file = f"{outputs_path}/{stem}.mxl"
    final_score.write('mxl', fp=output_file)
    print(f"Exported to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate harmonization from input melodies.")
    parser.add_argument("--genre", default=DEFAULT_GENRE, help="Genre weights to use for harmonization.")
    parser.add_argument("--weights-path", default=None, help="Optional explicit model weights path.")
    parser.add_argument("--chord-types-path", default=None, help="Optional explicit chord vocabulary path.")
    args = parser.parse_args()

    genre = normalize_genre(args.genre)
    weights_path = args.weights_path or get_weights_path(genre)
    chord_types_path = args.chord_types_path or get_chord_types_path(genre)

    if not os.path.exists(weights_path):
        raise FileNotFoundError(
            f"Missing weights for genre '{genre}' at {weights_path}. Train or fine-tune this genre first."
        )

    chord_types = load_chord_types(chord_types_path)
    if not chord_types:
        raise FileNotFoundError(
            f"Missing shared chord vocabulary at {chord_types_path}. Run loader with --build-global-vocab first."
        )

    print("Loading Inputs...")
    files = get_filenames(input_dir=INPUTS_PATH)
    if not files:
        print("No files found in inputs/")
        exit()
        
    data = convert_files(files, fromDataset=False)

    print("Loading Model...")
    # Weights are loaded inside build_model if path is provided
    model = build_model(SEGMENT_LENGTH, RNN_SIZE, NUM_LAYERS, DROPOUT,
                        weights_path=weights_path, chord_types_path=chord_types_path, training=False)

    print("Generating Harmonies...")
    for md, bd, kd, score_obj, fname in data:
        print(f"Processing {os.path.basename(fname)}...")
        chords = generate_chord(model, md, bd, kd, chord_types=chord_types)
        
        # DEBUG: Analyze generated chords for the first song
        unique_chords = np.unique([c for song in chords for c in song])
        print(f"DEBUG: Unique Indices Predicted: {unique_chords}")
        
        # Convert indices to readable labels to check if only 'R'
        labels_sample = [chord_types[int(c)] for song in chords for c in song if chord_types[int(c)] != 'R']
        print(f"DEBUG: Sample chords (excluding 'R'): {labels_sample[:20]}")
        print(f"DEBUG: Total 'R' (Rest) vs Total Indices: {sum(1 for song in chords for c in song if chord_types[int(c)] == 'R')} / {sum(len(s) for s in chords)}")

        export_music(score_obj, bd, chords, fname, chord_types=chord_types)
