# Environment, venv, models, and reproducible startup

Layout update, 8 October 2026: use the [master documentation](../README.md) and [structure/performance update](../validation/22_STRUCTURE_PERFORMANCE_AND_GAPS.md). Historical comparisons and measurements below describe their stated audit date. The older working tree is now archived; current paths and runtime are described in the update.

[Handbook index](../handbook/README.md)

## Historical versus inspected environment

| Item | Older workstation evidence | Current local inspection |
| --- | --- | --- |
| OS | Ubuntu documented; exact live workstation release unavailable | Linux 7.2.8-arch1-2, x86_64, glibc 2.44 |
| CPU/GPU | RTX A4000 described in guide, not independently inspected | Intel Core i5-1235U, 12 logical CPUs; current Python has CPU PyTorch |
| RAM | Unavailable | 24,278,656 KiB reported by `/proc/meminfo` (about 23.15 GiB) |
| Python | 3.10 shown in old log paths; old venv absent | `.venv/bin/python`: CPython 3.11.17 |
| Python manager | Old instructions use `python3.10 -m venv` | `.bootstrap` uv; `.venv/pyvenv.cfg` records uv 0.12.23, no system site packages |
| Whisper default | Saved config base/CPU/int8; old log CUDA/float16 | small/CPU/int8; four threads, 120-second central chunks |
| Node / npm | Exact former installed versions unavailable | Node v26.10.0 / npm 12.2.0 |
| FFmpeg | Not captured | n9.0.2 |

Current machine facts are a documentation-time inspection, not necessarily the exact host state when older measurements were recorded. CPU PyTorch does not prove whether the machine has any GPU hardware; it describes this environment's execution profile.

## How setup works

[`scripts/setup.sh`](../../scripts/setup.sh) requires Linux with `python3`, `ffmpeg`, `ffprobe`, `node`, and `npm`. It creates `.bootstrap` if needed, installs uv there, provisions Python 3.11, creates `.venv`, installs CPU torch/torchaudio, installs `environment/requirements-lock.txt`, and runs `npm ci` and a frontend build.

```bash
cd '/home/amitkumar/Music/MAI Project'
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --slides
.venv/bin/python scripts/validate_setup.py
bash scripts/start_app.sh
```

Setup and model provisioning require connectivity. Once weights are local, normal inference defaults to offline operation. These commands are handover instructions; they were not executed during this audit. The current environment already exists.

Use `.venv/bin/python` explicitly for scripts. Activation is optional:

```bash
source .venv/bin/activate
python --version
.bootstrap/bin/uv pip check --python .venv/bin/python
```

If relocating to another machine, rebuild the venv rather than copying it: its Python executable depends on uv's interpreter outside the repository. Transfer model/data artifacts separately with revision and hash records.

The uv-created environment currently has no `pip` module; use the bootstrap uv command above for dependency checks instead of `python -m pip`.

## Dependency roles and current versions

| Dependency | Installed version observed | Role |
| --- | --- | --- |
| torch / torchaudio | 2.5.1+cpu / 2.5.1+cpu | Silero/pyannote/model operations |
| numpy | 1.26.4 | Audio arrays and vectors |
| faster-whisper | 1.2.1 | Laptop Whisper inference |
| ctranslate2 | 4.8.2 | Quantized inference runtime used by faster-whisper |
| pyannote.audio | 3.3.2 | Optional speaker diarization |
| sentence-transformers | 3.4.1 | Slide/transcript semantic embeddings |
| FastAPI | 0.142.2 | Local API |
| pytest | 8.4.2 | Regression tests |

`environment/requirements.txt` specifies direct compatibility-sensitive pins and bounded ranges. `environment/requirements-lock.txt` captures a broader installed-version snapshot, including transitive packages and CPU wheel suffixes. The older requirements file had no version pins and omitted API/auth dependencies. Python lock versions are installation evidence, not evidence of trained model versions.

The React package and lock files are identical in the two supplied copies; major functionality changes are in frontend source. Check [frontend/package.json](../../frontend/package.json) for exact dependency declarations rather than assuming every UI improvement added a package.

## Provisioned weights

Observed under `models/hf/hub/`:

| Model | Snapshot revision present | Used for |
| --- | --- | --- |
| `Systran/faster-whisper-small` | `536b0662742c02347bc0e980a01041f333bce120` | Default laptop ASR |
| `Systran/faster-whisper-medium` | `08e178d48790749d25932bbc082711ddcfdfbc4f` | Optional laptop ASR |
| `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Default slide embeddings |
| `models/ggml-base.bin` | Local binary; record its SHA-256 for a release/experiment | Android whisper.cpp ASR |

No pyannote model snapshot was present in the inspected hub directory. No local ONNX diarization paths are configured. Ollama is optional and its models are not implied by the project model directory.

```bash
# One-time provisioning; explicit online operation:
.venv/bin/python scripts/download_models.py --asr-model medium
.venv/bin/python scripts/download_models.py --diarization
```

For pyannote, model-gate authorization and a locally stored `HF_TOKEN` are required. Read `config/.env.example`; keep the actual `config/.env` private. The provisioning command downloads ASR even when the selected additional flag is only `--slides` or `--diarization`.

Android expects multilingual GGML weights, not a faster-whisper directory. `bash android/setup.sh` explicitly provisions pinned whisper.cpp/NDK/model build dependencies. Build with `bash android/build.sh`; current direct build uses manifest version 0.4.0. Alternate Gradle files still advertise 0.3.1 and are not the verified handover path.

## Configuration precedence and defaults

`src/utils/config.py` loads `config/.env`, then YAML through a cached config loader. Environment overrides exist for selected `get()` keys. API job options override ASR model/language/vocabulary/speaker constraints within the processing call. Restart after YAML changes to avoid stale cached configuration.

| Setting | Default / meaning |
| --- | --- |
| `MAI_ASR_MODEL` | Overrides `asr.model_size`; YAML defaults to `small` |
| `MAI_ASR_LANGUAGE` | Overrides configured ASR language for compatible callers; API jobs explicitly carry their own selected language |
| `MAI_ASR_CHUNK_SECONDS` | Overrides central chunk duration; default 120 |
| `HF_HOME` | Defaults to project `models/hf` |
| `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` | Default `1`; launcher exports `1`; provisioning sets `0` |
| `HF_HUB_DISABLE_TELEMETRY` | Default `1` |
| `MAI_HOST` | API bind host, default `127.0.0.1` |
| `MAI_DB_PATH` | Defaults to `data/state/nexus_v2.db` |
| `MAI_RUNTIME_DIR`, `MAI_DATA_DIR` | Override private runtime and normalized recording directories |
| `MAI_MAX_UPLOAD_BYTES` | Default 1 GiB total per multipart job |
| `MAI_ALLOWED_ORIGINS` | Explicit comma-separated development origins |
| `MAI_SECRET_KEY` | Optional secret override; otherwise a private generated file |
| `alignment.method` | `embeddings`; optionally `tfidf` |
| `diarization.backend` | `pyannote`; optionally `sherpa-onnx` with manual models/dependency |

```bash
# Throughput profile or larger model:
MAI_ASR_CHUNK_SECONDS=300 bash scripts/start_app.sh
MAI_ASR_MODEL=medium bash scripts/start_app.sh

# Server-free complete meeting workflow:
.venv/bin/python scripts/process_meeting.py \
  --audio /path/to/meeting.m4a --meeting-id new_meeting --diarization auto
```

Use distinct meeting identifiers. `auto` diarization tolerates missing models and labels speech UNKNOWN; `required` fails on diarization failure; `off` deliberately disables it. Optional slides use `--ppt /path/to/slides.pptx`.

No training is executed by setup, model download, or normal inference. Changing YAML weights is heuristic configuration, not model training.
