import os

# Path setting
DATASETS_ROOT = "datasets"
WEIGHTS_ROOT = "weights"
BASELINE_GENRE = "baseline"
DEFAULT_GENRE = BASELINE_GENRE

CHORD_TYPES_GLOBAL_PATH = os.path.join(DATASETS_ROOT, "chord_types_global.bin")
INPUTS_PATH = "inputs"
OUTPUTS_PATH = "outputs"


def normalize_genre(genre=None):
    if genre is None:
        genre = DEFAULT_GENRE
    genre = str(genre).strip()
    return BASELINE_GENRE if genre in ("", BASELINE_GENRE) else genre


def get_dataset_dir(genre=None):
    genre = normalize_genre(genre)
    if genre == BASELINE_GENRE:
        return os.path.join(DATASETS_ROOT, BASELINE_GENRE)
    return os.path.join(DATASETS_ROOT, "genres", genre)


def get_scoresheets_dir(genre=None):
    return os.path.join(get_dataset_dir(genre), "scoresheets")


def get_corpus_path(genre=None):
    return os.path.join(get_dataset_dir(genre), "data_corpus.bin")


def get_weights_path(genre=None):
    genre = normalize_genre(genre)
    if genre == BASELINE_GENRE:
        return os.path.join(WEIGHTS_ROOT, BASELINE_GENRE, "weights.keras")
    return os.path.join(WEIGHTS_ROOT, "genres", genre, "weights.keras")


def get_chord_types_path(_genre=None):
    # Shared global vocabulary for baseline and every genre.
    return CHORD_TYPES_GLOBAL_PATH


# Backward-compatible constants mapped to baseline artifacts.
DATASET_PATH = get_dataset_dir(BASELINE_GENRE)
CORPUS_PATH = get_corpus_path(BASELINE_GENRE)
CHORD_TYPES_PATH = get_chord_types_path(BASELINE_GENRE)
WEIGHTS_PATH = get_weights_path(BASELINE_GENRE)

# 'loader.py'
EXTENSION = ['.musicxml', '.xml', '.mxl']
LOADER_MAX_WORKERS = 10

# '.model.py'
VAL_RATIO = 0.1
DROPOUT = 0.2
# RAM Impact: Increases input data size linearly.
SEGMENT_LENGTH = 32

# Model capacity: Higher (256/512) = "smarter" but slower/riskier overfitting; Lower (64/128) = faster/lighter.
# RAM Impact: High. Quadratic growth in weights. Best = 64 for current dataset.
RNN_SIZE = 128

# Network Depth: More layers (3-4) = can learn complex patterns; fewer (1-2) = simpler, faster training.
# RAM Impact: Linear growth in weights. Best = 3 for current dataset.
NUM_LAYERS = 3

# Training Batch: Higher (256+) = Faster epochs but less generalization; Lower (32/64) = Better accuracy but slower.
# RAM Impact: Very High. Linear growth. Best = 32 for current dataset.
BATCH_SIZE = 32

# Use training history to adjust usefull epochs is at lowest val_loss
EPOCHS = 3

# 'harmonizor.py'
RHYTHM_DENSITY = 0.5
CHORD_PER_BAR = False
REPEAT_CHORD = False
WATER_MARK = False
