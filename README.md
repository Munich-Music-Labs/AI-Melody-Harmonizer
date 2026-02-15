
# Generating Chords from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density

This is the source code of AutoHarmonizer2 an harmonic density-controllable melody harmonization system with flexible harmonic rhythm, trained/validated on Wikifonia.org's lead sheet dataset.  
  
This work is an adaptation to be integrated in https://pianoml.org.

This work is derived from original paper: [arXiv paper](https://arxiv.org/abs/2112.11122). by Shangda Wu, Yue Yang, Zhaowen Wang, Xiaobing Li, Maosong Sun and a fork of the original repository available at https://github.com/sander-wood/autoharmonizer



### What is harmonization?

Harmonization is the process of creating or adding chords (and sometimes voice-leading) that support a given melody in a musically coherent and stylistically appropriate way.  
In practice it means: given a single-line melody (or a lead sheet with melody + chords symbols), produce a full harmonic accompaniment — usually 3–4 voices — that sounds natural in a chosen style (classical, jazz, pop, baroque chorale, etc.).

### Why is harmonization difficult?

Even for experienced musicians, good harmonization is hard because it simultaneously requires solving many interdependent constraints:

- harmonic correctness (functional harmony, chord grammar of the style)
- voice-leading rules (smooth motion, avoid forbidden parallels, proper resolution of dissonances)
- melodic contour preservation (the original tune must still feel like the most important line)
- style & idiom (baroque ≠ romantic ≠ bebop ≠ modern pop)
- balance between surprise & predictability
- avoiding overused or cliché progressions when not wanted
- handling modulations, secondary functions, chromaticism, modal mixture…

Humans develop an intuition for these trade-offs over many years. Teaching a machine to make similar aesthetic decisions — without overfitting to one narrow style or producing bland “textbook” results — is currently one of the most challenging open problems in symbolic music generation.


## Repository Status

This project builds upon and enhances the excellent original work, with the goal of making it ready for integration into the open-source https://pianoml.org library.



See [UPGRADE_NOTES](UPGRADE_NOTES.md) for changes made to the original project.

  
## Install
  
```bash
python3 -m venv shared-venv
source shared-venv/bin/activate
pip install -r requirements.txt
```

## Melody Harmonization
1.　Put the MusicXML files in the `inputs` folder and run `harmonizer.py`. By default it uses the `DEFAULT_GENRE` configured in `config.py`.

   ```bash
   source shared-venv/bin/activate
   python harmonizer.py
   ```

2.　To force a specific genre checkpoint:

   ```bash
   python harmonizer.py --genre jazz
   ```

3.　The harmonized files are saved to the `outputs` folder.  
  
You can set the parameter RHYTHM_DENSITY∈[0, 1] in `config.py` to adjust the density of the generated chord progression. The higher the value of RHYTHM_DENSITY, the more chords will be generated, and vice versa.  

## Dataset And Weights Layout

Use this structure for baseline + per-genre fine-tuning:

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

## Baseline + Genre Fine-Tuning Workflow

1. Put baseline score sheets in `datasets/baseline/scoresheets/`.

2. Build baseline corpus and global vocabulary:

   ```bash
   python loader.py --genre baseline --build-global-vocab
   ```

3. Train baseline weights:

   ```bash
   python model.py --genre baseline --weights-out weights/baseline/weights.keras
   ```

4. Put genre score sheets in `datasets/genres/jazz/scoresheets/`.

5. Build a genre corpus using the shared vocabulary:

   ```bash
   python loader.py --genre jazz --use-global-vocab --unknown-chord-policy map_to_R
   ```

6. Fine-tune genre weights from baseline:

   ```bash
   python model.py --genre jazz \
     --base-weights weights/baseline/weights.keras \
     --weights-out weights/genres/jazz/weights.keras
   ```

7. Harmonize using genre weights:

   ```bash
   python harmonizer.py --genre jazz
   ```

Notes:
- `loader.py` now cleans corpus artifacts only; it does not delete baseline weights.
- `loader.py` reads training score sheets from `datasets/<target>/scoresheets/`.
- `model.py` prevents accidental overwrite by rejecting identical `--base-weights` and `--weights-out`.
- The shared global vocabulary keeps baseline and genre output heads compatible.

After training, you can use `harmonizer.py` to harmonize music with chord progressions that fit the selected musical style.   
  
If you need to finetune the parameters, you can do so in `config.py`. It is not recommended to change the parameters in other files.


## Model performance

| Best Val Loss | Train Loss @ Best | Best Val Acc | Train Acc @ Best | Best Epoch |
|---------------|-------------------|--------------|------------------|------------|
| 0.41651       | 0.36988           | 0.93393      | 0.92914          | 3          |

- Validation Loss of 0.41651 reasonable for NLL harmonization
- train is still noticeably better than val (gap ~0.047)
- 93.393% impressive accuracy
- val acc > train acc (by ~0.48%)

![Training history](training_history.png)

## Bibliography

> Wu, S., Yang, Y., Wang, Z., Li, X., & Sun, M. (2023). Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density. arXiv:2112.11122 [cs.SD]. [https://arxiv.org/abs/2112.11122](https://arxiv.org/abs/2112.11122)

```
@misc{wu2023generatingchordprogressionmelody,
  title={Generating Chord Progression from Melody with Flexible Harmonic Rhythm and Controllable Harmonic Density},
  author={Shangda Wu and Yue Yang and Zhaowen Wang and Xiaobing Li and Maosong Sun},
  year={2023},
  eprint={2112.11122},
  archivePrefix={arXiv},
  primaryClass={cs.SD},
  url={https://arxiv.org/abs/2112.11122},
}
```






