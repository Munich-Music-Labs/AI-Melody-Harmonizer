# AI Melody Harmonizer

Generate chord progressions from a melody with flexible harmonic rhythm and controllable harmonic density.

**AI Melody Harmonizer** is a harmonic-density-controllable melody harmonization system. The baseline model is bootstrapped from the [Wikifonia.org](http://www.wikifonia.org/) lead sheet dataset (used in the original paper), and we are actively gathering additional data to fine-tune the model toward genre-specific styles (jazz, pop, etc.).

> **Built on the original [AutoHarmonizer](https://github.com/sander-wood/autoharmonizer) by [Sander Wood](https://github.com/sander-wood) (Shangda Wu).**
> This project is a fork of that repository and an implementation of the paper [*Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density*](https://arxiv.org/abs/2112.11122) by Shangda Wu, Yue Yang, Zhaowen Wang, Xiaobing Li, and Maosong Sun.
> Released under the MIT License (© 2021 Sander Wood) — see [LICENSE](LICENSE). All credit for the original architecture and research goes to the upstream authors; this fork only adapts and extends their work.

---

## Table of Contents

- [Background](#background)
- [What's New in This Fork](#whats-new-in-this-fork)
- [Installation](#installation)
- [Quick Start: Harmonize a Melody](#quick-start-harmonize-a-melody)
- [Dataset and Weights Layout](#dataset-and-weights-layout)
- [Training Workflow](#training-workflow)
- [Model Performance](#model-performance)
- [Acknowledgments and Credits](#acknowledgments-and-credits)
- [Bibliography](#bibliography)
- [License](#license)

---

## Background

### What is harmonization?

Harmonization is the process of creating or adding chords (and sometimes voice-leading) that support a given melody in a musically coherent and stylistically appropriate way.

In practice it means: given a single-line melody (or a lead sheet with melody + chord symbols), produce a full harmonic accompaniment — usually 3–4 voices — that sounds natural in a chosen style (classical, jazz, pop, baroque chorale, etc.).

### Why is harmonization difficult?

Even for experienced musicians, good harmonization is hard because it simultaneously requires solving many interdependent constraints:

- harmonic correctness (functional harmony, chord grammar of the style)
- voice-leading rules (smooth motion, avoid forbidden parallels, proper resolution of dissonances)
- melodic contour preservation (the original tune must still feel like the most important line)
- style and idiom (baroque ≠ romantic ≠ bebop ≠ modern pop)
- balance between surprise and predictability
- avoiding overused or cliché progressions when not wanted
- handling modulations, secondary functions, chromaticism, modal mixture…

Humans develop intuition for these trade-offs over many years. Teaching a machine to make similar aesthetic decisions — without overfitting to one narrow style or producing bland "textbook" results — remains one of the most challenging open problems in symbolic music generation.

---

## What's New in This Fork

This project builds upon and enhances the excellent original work.

### Architectural Improvements

- **Fused inputs.** Melody, beat, and key are now concatenated *before* the LSTM layers. The model processes `[Note + Rhythm + Key]` as a single unified context instead of three isolated streams.
- **Native embeddings.** Replaced the expensive `OneHot + Dense` blocks with `keras.layers.Embedding`, which drastically reduces RAM/VRAM usage and gives a richer semantic representation of musical concepts.

### Dependency Upgrades

| Package      | Before  | After     | Why                          |
|--------------|---------|-----------|------------------------------|
| TensorFlow   | 2.14.0  | ≥ 2.18.0  | Native NumPy 2 support       |
| NumPy        | —       | ≥ 2.0.0   | Explicitly pinned            |
| music21      | 7.3.3   | ≥ 9.1.0   | NumPy 2 compatibility        |

### Memory and Performance Optimizations (`model.py`)

**`DataGenerator`**
- Yields integer indices (`uint8` / `uint16`) instead of massive one-hot float arrays — vectors are now built on the GPU via the Embedding layers.
- Conversion to NumPy arrays with optimized dtypes (`uint8` / `uint16`).
- Added `on_epoch_end()` for efficient shuffling via indices.
- Indexing by indices instead of repeated slicing.
- ~8× memory reduction for MIDI values (`uint8` vs `int64`).
- Fixes CPU→GPU bandwidth bottlenecks and RAM saturation.

**`create_training_data()`**
- Pre-allocation of NumPy arrays (avoids repeated `append`).
- Optimized dtypes: `uint8` for melody/beat/key, `uint16` for chords.
- Final trim to free unused space.

### Repository Cleanup

- Switched dependency and environment management to [uv](https://docs.astral.sh/uv/) — `pyproject.toml` + `uv.lock` are the source of truth, with Python 3.10 pinned via `.python-version`. A `requirements.txt` is kept as a pip fallback.
- Modularized `model.py` structure and removed redundant logic in data loading.
- Removed non-essential artefacts (`.bin`) from git; generation workflow is now code-driven.
- Migrated datasets to `.tgz` archives.

---

## Installation

This project uses [**uv**](https://docs.astral.sh/uv/) for dependency and environment management. Python 3.10 is pinned via `.python-version` and uv will pick it up automatically.

### Recommended: uv

```bash
# Install uv once: https://docs.astral.sh/uv/getting-started/installation/
uv sync
```

`uv sync` reads `pyproject.toml` + `uv.lock`, creates a virtual environment in `.venv/`, and installs every dependency at the locked version. You don't need to activate the venv manually — prefix commands with `uv run` (see below).

### Alternative: pip + venv

If you'd rather not use uv, a `requirements.txt` is kept as a fallback:

```bash
python3 -m venv shared-venv
source shared-venv/bin/activate
pip install -r requirements.txt
```

In this case, activate `shared-venv` before running any of the commands below and drop the `uv run` prefix.

---

## Quick Start: Harmonize a Melody

1. Put your MusicXML files in the `inputs/` folder.
2. Run the harmonizer (uses `DEFAULT_GENRE` from `config.py`):

   ```bash
   uv run python harmonizer.py
   ```

3. To force a specific genre checkpoint:

   ```bash
   uv run python harmonizer.py --genre jazz
   ```

4. Harmonized files are saved to the `outputs/` folder.

> **Tip:** Adjust `RHYTHM_DENSITY ∈ [0, 1]` in `config.py` to control how many chords are generated. Higher values produce denser progressions.

---

## Dataset and Weights Layout

Use this structure for the baseline plus per-genre fine-tuning:

```text
datasets/
  baseline/
    scoresheets/            # baseline lead sheets (MusicXML)
    data_corpus.bin         # generated from baseline scoresheets
  genres/
    jazz/
      scoresheets/          # jazz lead sheets
      data_corpus.bin       # generated from jazz scoresheets
    pop/
      scoresheets/
      data_corpus.bin
  chord_types_global.bin    # shared chord vocabulary

weights/
  baseline/weights.keras
  genres/
    jazz/weights.keras
    pop/weights.keras
```

---

## Training Workflow

End-to-end recipe for training a baseline model and fine-tuning per-genre variants.

1. Put baseline score sheets in `datasets/baseline/scoresheets/`.

2. Build the baseline corpus and the global vocabulary:

   ```bash
   uv run python loader.py --genre baseline --build-global-vocab
   ```

3. Train baseline weights:

   ```bash
   uv run python model.py --genre baseline --weights-out weights/baseline/weights.keras
   ```

4. Put genre score sheets in `datasets/genres/jazz/scoresheets/`.

5. Build a genre corpus using the shared vocabulary:

   ```bash
   uv run python loader.py --genre jazz --use-global-vocab --unknown-chord-policy map_to_R
   ```

6. Fine-tune genre weights from the baseline:

   ```bash
   uv run python model.py --genre jazz \
     --base-weights weights/baseline/weights.keras \
     --weights-out weights/genres/jazz/weights.keras
   ```

7. Harmonize with the new genre weights:

   ```bash
   uv run python harmonizer.py --genre jazz
   ```

**Notes**

- `loader.py` cleans corpus artefacts only; it does not delete baseline weights.
- `loader.py` reads training score sheets from `datasets/<target>/scoresheets/`.
- `model.py` prevents accidental overwrites by rejecting identical `--base-weights` and `--weights-out`.
- The shared global vocabulary keeps baseline and genre output heads compatible.
- Most parameters can be tuned in `config.py`. Changing parameters in other files is not recommended.

---

## Model Performance

| Best Val Loss | Train Loss @ Best | Best Val Acc | Train Acc @ Best | Best Epoch |
|---------------|-------------------|--------------|------------------|------------|
| 0.41651       | 0.36988           | 0.93393      | 0.92914          | 3          |

- Validation loss of **0.41651** is reasonable for NLL harmonization.
- Training is still noticeably better than validation (gap ≈ 0.047).
- **93.39%** validation accuracy.
- Validation accuracy slightly exceeds training accuracy (by ≈ 0.48%).

![Training history](training_history.png)

---

## Acknowledgments and Credits

This project would not exist without the work of the original authors. Please credit them when using or referencing this codebase.

- **Original author and upstream repository:** [Sander Wood](https://github.com/sander-wood) (Shangda Wu) — [`sander-wood/autoharmonizer`](https://github.com/sander-wood/autoharmonizer). The core architecture, training pipeline, and original implementation are his work.
- **Paper authors:** Shangda Wu, Yue Yang, Zhaowen Wang, Xiaobing Li, and Maosong Sun — [*Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density*](https://arxiv.org/abs/2112.11122) (arXiv:2112.11122).
- **Baseline training data:** [Wikifonia.org](http://www.wikifonia.org/) lead sheet dataset (as used in the original paper). Additional genre-specific datasets are being collected for fine-tuning.

This fork adds engineering improvements (memory optimizations, native embeddings, fused inputs, dependency upgrades, baseline + per-genre fine-tuning workflow). All conceptual credit for the harmonization model itself belongs to the upstream authors.

---

## Bibliography

> Wu, S., Yang, Y., Wang, Z., Li, X., & Sun, M. (2023). *Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density.* arXiv:2112.11122 [cs.SD]. <https://arxiv.org/abs/2112.11122>

```bibtex
@misc{wu2023generatingchordprogressionmelody,
  title         = {Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density},
  author        = {Shangda Wu and Yue Yang and Zhaowen Wang and Xiaobing Li and Maosong Sun},
  year          = {2023},
  eprint        = {2112.11122},
  archivePrefix = {arXiv},
  primaryClass  = {cs.SD},
  url           = {https://arxiv.org/abs/2112.11122},
}
```

---

## License

This project is distributed under the **MIT License**, inherited from the original [AutoHarmonizer](https://github.com/sander-wood/autoharmonizer) repository.

> Copyright © 2021 Sander Wood — original author and copyright holder.
> Modifications and additions in this fork are also released under the MIT License.

See [LICENSE](LICENSE) for the full text.
