# "Hey TARS" wake word model

`hey_tars.onnx` and `hey_tars_meta.json` are the TARS-AI community's wake word model,
copied unchanged from [TARS-AI](https://github.com/TARS-AI-Community/TARS-AI)
(`src/tts/`, V3 branch). By Charles-Olivier Dion (AtomikSpace) and the TARS-AI Community,
CC-BY-NC 4.0: personal, non-commercial use with credit.

The feature extraction in `../wake.py` is adapted from their `module_atomik.py` so the
model sees audio exactly the way it was trained.
