FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/models/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    MAI_HOST=0.0.0.0 \
    MAI_PORT=7860 \
    MAI_ASR_MODEL=small \
    MAI_ASR_DEVICE=cpu \
    MAI_ASR_COMPUTE_TYPE=int8

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY environment/requirements-lock.txt environment/requirements-lock.txt
RUN pip install --no-cache-dir torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r environment/requirements-lock.txt \
    && pip check

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p state/data state/outputs state/runtime \
    && ln -s state/data data \
    && ln -s state/outputs outputs \
    && ln -s state/runtime .runtime \
    && chown -R 1000:1000 /app

COPY --chown=1000:1000 backend/ backend/
COPY --chown=1000:1000 src/ src/
COPY --chown=1000:1000 config/config.yaml config/config.yaml
COPY --chown=1000:1000 scripts/download_models.py scripts/download_speaker_models.py scripts/validate_setup.py scripts/
COPY --chown=1000:1000 models/discussion/model.joblib models/discussion/manifest.json models/discussion/

USER 1000:1000
RUN python scripts/download_models.py --asr-model small --slides \
    && python scripts/download_speaker_models.py \
    && python scripts/validate_setup.py

EXPOSE 7860
CMD ["python", "-m", "backend.api"]
