---
title: Meet IQ Backend
emoji: 🎙️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Meet IQ backend

FastAPI API and CPU meeting analysis. The React frontend can be hosted separately on Render.

## Create the upload folder

From the complete local project, run:

```bash
.venv/bin/python scripts/package_huggingface.py
```

Upload the **contents** of the printed folder to the root of a Hugging Face **Docker Space**. Do not upload the ZIP as the only file or nest the whole folder under another directory. The package contains the Dockerfile, this Space README, backend, complete Python source, configuration, dependency lock, model download scripts and the trained discussion model. Private databases, recordings, credentials, evaluation outputs and the frontend are excluded.

Creating Docker Spaces currently requires an eligible paid plan; CPU Basic hardware itself has no hourly compute charge. Confirm eligibility in the account before relying on this route. Use Public or Protected app visibility for access from a public frontend; a Private Space is not a public API.

## Settings

Add these **Variables** in the Space Settings, replacing example hostnames:

```dotenv
MAI_PUBLIC_URL=https://YOUR-ACTUAL-SPACE-HOST.hf.space
MAI_ALLOWED_ORIGINS=https://YOUR-FRONTEND.onrender.com
MAI_ALLOW_REGISTRATION=1
```

Use the actual `hf.space` application URL, without `/api` or a trailing path. `MAI_PUBLIC_URL` makes recording URLs point to the backend when the frontend has a separate origin. For multiple frontend origins, use a comma-separated list without spaces. Before Render exists, a local browser frontend can be allowed with `http://127.0.0.1:5174`.

Add **Secret** `MAI_SECRET_KEY` with a stable random value. Generate one locally with:

```bash
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Do not commit its value. Registration is open when `MAI_ALLOW_REGISTRATION=1`; set it to `0` after creating the intended accounts if access should be limited to them. Run one backend process. The Docker image already configures host `0.0.0.0`, port `7860`, speech model `small`, CPU and int8.

The first image build installs the CPU Python environment and downloads the small speech, MiniLM slide and public ONNX speaker models. It includes the trusted trained discussion artifact. Normal meeting inference uses these local weights; no Hugging Face token is needed for these public model downloads.

## Persistent state

All mutable application state is linked beneath **`/app/state`**:

| Image path | State path |
| --- | --- |
| `/app/data` | `/app/state/data` |
| `/app/outputs` | `/app/state/outputs` |
| `/app/.runtime` | `/app/state/runtime` |

This includes SQLite accounts/history, recordings, processed files, resume checkpoints, reports and the fallback JWT secret. Models are baked into the image separately.

Default Space disk is ephemeral: accounts and recordings can disappear on restart/rebuild. The links consolidate state; they do not create persistence by themselves. A durable mount must cover `/app/state`, be writable by UID/GID 1000, and support SQLite transactions, file locking and atomic rename. Do not assume an object-storage bucket mount has those guarantees; validate them before using it for the live database. Without verified durable storage, use the deployment as a temporary demonstration and export important reports.

For a local Docker persistence test, a named volume can cover this directory:

```bash
docker build -t meetiq-backend .
docker run --name meetiq-backend -p 127.0.0.1:7860:7860 \
  --mount source=meetiq-state,target=/app/state \
  -e MAI_PUBLIC_URL=http://127.0.0.1:7860 \
  -e MAI_ALLOWED_ORIGINS=http://127.0.0.1:5174 \
  meetiq-backend
```

## Verify before connecting Render

Open `https://YOUR-ACTUAL-SPACE-HOST.hf.space/docs` for the API interface and `/api/health` for readiness. Check `asr_ready` and `diarization.ready` are true. The image serves the API only; the root `/` does not contain the React website.

Test registration/login, multiple audio and PPT uploads, cumulative progress, final analysis, token-protected audio playback, exports, and saved history after a restart. Cloud CPU performance must be measured on the selected hardware.

On Render, use a Static Site with root `frontend`, build `npm ci && npm run build`, publish `dist`, and build variable `VITE_API_URL=https://YOUR-ACTUAL-SPACE-HOST.hf.space/api`. Add the Render origin to `MAI_ALLOWED_ORIGINS` and restart the Space after changing runtime settings.

Official references: [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker), [eligibility and hardware](https://huggingface.co/docs/hub/spaces-overview), [Space storage](https://huggingface.co/docs/hub/spaces-storage).
