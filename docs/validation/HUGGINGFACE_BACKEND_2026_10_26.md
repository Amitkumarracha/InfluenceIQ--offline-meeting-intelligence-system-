# Hugging Face backend preparation and local validation

26 October 2026. Backend upload package prepared; no Hugging Face Space or Render site was created or modified.

## Changes

- Root `Dockerfile`: Python 3.11, locked CPU dependencies, FFmpeg, public speech/slide/speaker model provisioning during build, non-root UID/GID 1000, port 7860, one API process, no frontend build.
- `.dockerignore`: includes backend deployment source and the trusted discussion model; excludes private workstation state and unrelated project artifacts.
- `scripts/package_huggingface.py`: creates a new backend-only folder and ZIP from explicit files and Python source. Includes the trained discussion model despite the main Git ignore rules; rejects missing or symlinked deployment inputs.
- `deployment/huggingface/README.md`: Space metadata, variables, secret setup, storage requirements, upload and Render connection instructions. Copied to the package root as `README.md`.
- `backend/api.py`: optional `MAI_PUBLIC_URL` prefixes signed recording URLs. This fixes audio playback when Render serves the frontend and Hugging Face serves the API. Unset preserves local relative URLs.
- Mutable `data`, `outputs` and `.runtime` paths in the image link beneath `/app/state` so a compatible durable mount can cover accounts, audio, checkpoints, reports and the fallback signing secret together.

## Verification

The API, account-sync, multi-upload, report-scope, website-regression, web-processing and new cloud-deployment tests passed: **59 tests**, one existing Starlette/httpx deprecation warning. New checks cover an allowed Render origin, rejected untrusted origin, authenticated upload, absolute signed audio URL, account isolation, media-token scope and package exclusion of private files.

The Docker build installed the locked CPU stack and `pip check` reported no dependency conflicts. Speech, slide and speaker readiness checks passed. Docker Desktop was killed by the host OOM killer while importing/unpacking the final image; its service was restarted and the saved image recovered successfully. This is a local host-memory limitation, not a passed uninterrupted build claim.

The recovered image `meetiq-backend:validation-20261026` passed a real isolated runtime check limited to **2 CPUs / 4 GiB**:

| Check | Result |
| --- | --- |
| ASR, slide and speaker models available | Passed |
| Registration and allowed-origin preflight | Passed |
| Two audio parts and two presentations uploaded | Passed |
| Input audio | 30 seconds total from existing public English AMI fixtures |
| Post-upload processing wall time | 33.821 seconds |
| Final transcript | 14 segments |
| Final slides | 2 |
| Signed audio playback and JSON export | Passed |
| Cross-account meeting isolation | Passed |
| Account, report, audio and signing secret after container replacement | Passed with the same Docker named volume |

The isolated test container and its synthetic-account volume were removed. The existing laptop backend on port 8001 remained healthy. Docker Desktop was restarted after validation when no containers were running to release the guest-memory pressure; no Docker resource settings were changed.

Machine-readable evidence: `outputs/evaluation/huggingface_backend_20261026.json`. The isolated smoke-check source and raw result are under `.runtime/validation/huggingface-20261026/`.

## Upload artifact

Prepared folder: `.runtime/deployment/hf-backend-nm49ov2l/`.

Prepared ZIP: `.runtime/deployment/hf-backend-nm49ov2l.zip` (1,928,285 bytes at packaging time). Extract and upload its **contents** to the root of a Docker Space; the ZIP alone is not a deployable Space. To regenerate from the current source, run `.venv/bin/python scripts/package_huggingface.py` and use its newly printed folder.

Configure `MAI_PUBLIC_URL` to the actual HTTPS `hf.space` application origin; configure `MAI_ALLOWED_ORIGINS` for the frontend origin, `MAI_ALLOW_REGISTRATION` for intended account creation, and a stable private `MAI_SECRET_KEY`. The root `/` has no React website in this image; use `/docs` and `/api/health` to check the backend before connecting Render.

## Limits

No provider credentials were configured, no remote image build or upload occurred, and cloud latency and persistence were not verified. The measured short fixture is not a benchmark of accuracy or general throughput. Optional OCR remains disabled.

Default Hugging Face Space disk is ephemeral. Docker named-volume persistence proves the image's state layout; it does not certify any provider bucket mount for SQLite file locking/transactions or atomic rename. Use compatible durable storage or treat the Space as a temporary demo and export important results. Current Docker Space creation eligibility may require a paid Hugging Face plan; CPU Basic's lack of hourly compute cost does not establish free account eligibility.
