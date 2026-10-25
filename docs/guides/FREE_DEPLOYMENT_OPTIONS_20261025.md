# Free deployment options for the meeting-intelligence website

Checked against project source and official provider documentation on 25 October 2026. This is a deployment guide and comparison; no cloud resources or public tunnel were created. Account-specific credit balances and regional capacity were not inspected.

## Recommendation

- Presentation today: keep the working laptop backend and expose it temporarily with Cloudflare Quick Tunnel. This has no cloud compute bill, but the laptop must remain awake and connected.
- Independent cloud hosting using your existing AWS account: use a single x86 Ubuntu EC2 instance with 4–8 GiB RAM only if your account's remaining credits and plan cover it. Prefer testing with 8 GiB. The Free Tier label alone does not establish that your particular usage costs zero.
- Ongoing free cloud candidate: Oracle A1 Always Free, subject to availability and verifying the project's pinned Python/ML dependencies on ARM.
- Hugging Face: technically suitable CPU RAM, but current Docker/CPU Space creation requires a paid subscription. Its free Gradio ZeroGPU exception requires adapting this application.
- Render Free: suitable for the built frontend, insufficient for the complete ML backend.

## What this app needs

The backend serves the built React website and FastAPI API from one port. It runs a serialized background ML executor, stores accounts/history in SQLite, and stores audio, job checkpoints, processed inputs and reports on disk. A persistent single server is the simplest fit.

The saved ASR measurements in `outputs/evaluation/efficiency-results.json` recorded process peaks of 1,479.7 and 1,516.7 MB. These are historical speech experiments, not a new measurement of the entire current pipeline. They already exceed typical 512 MB free web plans. Start cloud evaluation with 2 vCPUs and 4–8 GiB RAM, preferably 8 GiB; this is an engineering recommendation, not a certified minimum or performance guarantee. Do not expect a small free CPU to outperform the laptop.

Use the default `small` speech model and CPU `int8` first. The speech, speaker and slide models must be provisioned once with internet access. Ordinary inference then runs locally on the server. A GPU, paid AI API and separate database server are not required for this initial deployment.

## Provider comparison

| Option | Free offer / condition | Fit for this project |
| --- | --- | --- |
| Laptop + Cloudflare Quick Tunnel | Temporary public URL; your own computation | Fastest presentation route; laptop-dependent |
| AWS EC2 | Eligible credits / active Free account plan | Good single-server fit with enough RAM; time/credit limited |
| Oracle A1 | Current Always Free equivalent: 2 OCPUs + 12 GB total | Promising ongoing free option; ARM and capacity checks required |
| Hugging Face Docker CPU Basic | 2 CPU cores, 16 GB RAM, 50 GB ephemeral disk; paid-plan creation eligibility | Good demo hardware if eligible; not universally $0 |
| Hugging Face ZeroGPU | Up to 2 free Gradio Spaces for qualifying personal accounts | Application/dependency adaptation required; not a direct Docker deployment |
| Render Free web service | 0.1 CPU, 512 MB RAM; idle sleeping; ephemeral files | Full ML backend does not fit |
| Google Cloud | Eligible new-user $300 / 90-day trial | Suitable larger VM during trial; ongoing free e2-micro is too small |
| Azure | Students: eligible $100 / 12 months; general eligible trial: $200 / 30 days | Suitable larger VM within credits; not indefinitely free |
| Railway Free | $5 / 30-day trial, then $1 monthly resource credit; 1 GB RAM during trial, 0.5 GB afterward | Insufficient RAM for this pipeline |
| Koyeb Free | 0.1 vCPU, 512 MB RAM, 2 GB SSD; no persistent volumes | Insufficient RAM and no durable local app state |
| Fly.io trial | 2 total VM hours or 7 days, whichever first; up to 4 GB RAM | Very short test only; not ongoing free hosting |
| Render Static / Cloudflare Pages / Vercel Hobby | Static frontend within applicable free limits | Must connect to a separately hosted backend |

Provider terms: [AWS EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html), [Oracle](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Hugging Face](https://huggingface.co/docs/hub/spaces-overview), [Render compute](https://render.com/docs/compute-plans), [Google](https://docs.cloud.google.com/free/docs/free-cloud-features), [Azure Students](https://azure.microsoft.com/en-us/free/students/), [Azure general trial](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/avoid-charges-free-account), [Railway](https://railway.com/pricing), [Koyeb](https://www.koyeb.com/docs/reference/instances), [Fly.io](https://docs.fly.io/about/free-trial).

## 1. Presentation now: laptop and temporary HTTPS URL

The existing backend was responding at `http://127.0.0.1:8001/api/health` when this guide was prepared. Check it first:

```bash
cd '/home/amitkumar/Music/MAI Project'
curl --fail http://127.0.0.1:8001/api/health
```

If it is already running, leave it running. If stopped, launch it in a separate terminal, using the existing account:

```bash
cd '/home/amitkumar/Music/MAI Project'
MAI_PORT=8001 bash deployment/run_workstation.sh
```

In another terminal, install the Linux x86_64 tunnel binary and start it:

```bash
cd '/home/amitkumar/Music/MAI Project'
mkdir -p .runtime
curl --fail --location https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 --output .runtime/cloudflared
chmod +x .runtime/cloudflared
.runtime/cloudflared tunnel --url http://127.0.0.1:8001
```

Open the printed `https://...trycloudflare.com` URL on another phone/network and log in. Both website and API use this URL. Do not expose Vite port 5174 instead of the backend. Keep the laptop awake, online and both processes running. The URL disappears when the tunnel stops. Tunnel/proxy upload limits may be lower than the app's own 1 GB limit; use a short presentation test recording first. This is a temporary demonstration, not independently hosted cloud inference.

[Official Quick Tunnel instructions and access behavior](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

## 2. AWS: use the existing account only after checking its actual offer

Open **Billing and Cost Management → Free Tier / Credits**. Check the account plan, credit balance, expiry, regional instance availability and estimated instance/storage/network costs.

- Accounts created before 15 July 2025 used the older 12-month EC2 benefit. By this guide's date, that original 12-month window has elapsed. Separate promotional credits may still exist.
- Newer accounts receive $100 signup credits and can earn up to $100 more. The Free account plan lasts six months or until credits are exhausted, whichever first. A Paid account plan can bill usage beyond applicable credits. A Free account plan closes when its allowance ends unless upgraded, so export data before expiry.
- AWS currently lists `c7i-flex.large` and `m7i-flex.large` among newer-account Free Tier-eligible instance types. They have 2 vCPUs with 4 and 8 GiB RAM respectively. Check that your account and chosen region permit them; eligibility still consumes credits.

[EC2 account-date rules](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html), [account plans and credit expiry](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html), [C7i specs](https://aws.amazon.com/ec2/instance-types/c7i/), [M7i specs](https://aws.amazon.com/ec2/instance-types/m7i/).

Procedure:

1. EC2 → Launch instance → Ubuntu Server x86_64. Select an eligible 4–8 GiB instance covered by your actual credits. Do not choose a 1 GiB micro instance for this full pipeline.
2. Start with roughly 30–50 GB persistent disk for the OS, environment, models and a few recordings. This is a capacity suggestion, not a promise that this disk amount is free.
3. Restrict SSH to your IP. Use a TLS reverse proxy or tunnel for browser access; keep the Python API on loopback behind it. HTTPS is also needed for browser microphone access remotely.
4. Transfer a clean reviewed copy of the application and required trained model; follow the common Ubuntu setup below. Rebuild the Python environment on the VM.
5. Run one application process under systemd, keeping all runtime state on its persistent disk.
6. Open its HTTPS URL and test accounts, uploads, analysis, reports and restart persistence.
7. After the demo, review/delete resources you no longer need. Stopping a VM can leave separately billable storage, addresses or other resources. On a Paid plan, budget alerts do not themselves cap charges.

One VM is sufficient for this initial architecture. RDS, load balancers, Kubernetes and NAT gateways are not needed to get this version online.

## 3. Oracle Cloud Always Free

Current official documentation gives the A1 free allocation as 1,500 OCPU-hours and 9,000 GB-hours monthly, equivalent to **2 OCPUs / 12 GB RAM** for an Always Free tenancy. The block-volume pool is 200 GB total across eligible boot/block volumes. Use the console's current entitlement rather than older articles promising 4 OCPUs / 24 GB. Capacity shortages can prevent creation, and idle free instances may be reclaimed.

Procedure:

1. Create/verify the OCI account; use its home region.
2. Compute → Create instance → Ubuntu ARM image → `VM.Standard.A1.Flex`, explicitly within your Always Free limits. Allocate one 2 OCPU / 12 GB instance if the console allows it.
3. Keep all boot/block volumes within the total free allocation. Allow SSH from your IP and configure HTTPS access.
4. Rebuild the environment for ARM. The project's pinned CPU PyTorch/torchaudio, CTranslate2 and Sherpa-ONNX wheels must all install and run; the existing x86 environment cannot be copied. The current setup script is not ARM-certified.
5. Provision models, run readiness checks, then perform a real audio-plus-PPT analysis. Proceed only after this passes.
6. Use the common single-process setup and keep independent backups of important reports.

[Official Oracle allocation, capacity and reclamation policy](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

## 4. Hugging Face Spaces

The current rules distinguish hardware cost from subscription eligibility: CPU Basic has no hourly compute cost, but creating a Docker/CPU compute Space requires PRO for personal accounts or Team/Enterprise for organizations. Static Spaces remain free. CPU Basic offers 2 CPU cores, 16 GB RAM and 50 GB nonpersistent disk. Confirm any existing/sponsored entitlement in your account.

If eligible:

1. Create a Space → Docker SDK → CPU Basic.
2. Add a Dockerfile that installs FFmpeg, Python 3.11, project CPU dependencies, builds the frontend with a compatible Node version, and provisions only the required models. The repository currently has no ready Dockerfile.
3. Configure Space README metadata:

```yaml
---
title: Meeting Intelligence
sdk: docker
app_port: 7860
---
```

4. Start the backend inside the container with `MAI_HOST=0.0.0.0`, `MAI_PORT=7860`, CPU/int8 and a controlled registration policy. Serve `frontend/dist` from the same backend.
5. Set the JWT secret using Space Secrets. Confirm all necessary paths are writable by the container user.
6. Decide whether temporary demo data is acceptable. The default disk is nonpersistent; permanent accounts/uploads/reports need an explicit durable storage design. Pointing only SQLite at another directory does not persist the remaining artifacts.
7. Push the clean app, wait for its build, inspect model readiness and test the Space URL. Free hardware may sleep.

Free alternative: qualifying personal accounts with verified email and age over 30 days can host up to two **Gradio ZeroGPU** Spaces. This is exclusively a Gradio SDK route; our existing React/FastAPI application, Python 3.11/PyTorch 2.5.1 stack and CTranslate2 inference need compatibility work against ZeroGPU's supported environment. It is a separate adaptation, not a quick setting change.

[Spaces eligibility/hardware](https://huggingface.co/docs/hub/spaces-overview), [Docker setup](https://huggingface.co/docs/hub/spaces-sdks-docker), [ZeroGPU rules and supported stack](https://huggingface.co/docs/hub/spaces-zerogpu).

## 5. Render

Free Web Service has 512 MB RAM / 0.1 CPU. It sleeps after 15 minutes without inbound traffic and loses changed local files on restart/redeploy/spindown. Free services cannot attach persistent disks. Free Postgres expires after 30 days, and this app currently uses SQLite directly anyway. The full pipeline is not a practical Render Free deployment.

Free frontend procedure:

1. Host the backend on the laptop tunnel, AWS or another suitable server first.
2. Render → New → Static Site → connect a clean project repository.
3. If the root is the repository root, use build command `npm --prefix frontend ci && npm --prefix frontend run build` and publish directory `frontend/dist`.
4. Set build environment variable `VITE_API_URL=https://YOUR-BACKEND/api` before building.
5. On the backend, set `MAI_ALLOWED_ORIGINS=https://YOUR-STATIC-SITE` and restart it. Rebuild the frontend if its backend URL changes.
6. Test registration/login and authenticated uploads across the two HTTPS origins.

If choosing a paid full-backend service later, add the Docker build, enough RAM and persistent storage. Render supplies `PORT`; map it to this app explicitly using `MAI_HOST=0.0.0.0 MAI_PORT="$PORT" .venv/bin/python -m backend.api` in an image that installs the environment at that path. The app reads `MAI_PORT`, not `PORT` automatically.

[Render compute](https://render.com/docs/compute-plans), [free-service limitations](https://render.com/docs/free).

## 6. Google Cloud and Azure

**Google Cloud:** eligible new users receive $300 for 90 days. Its ongoing free Compute Engine allocation is an e2-micro in selected US regions, not an adequately sized VM for this complete pipeline. During the trial, create a 4–8 GiB Ubuntu x86 VM whose estimated compute/disk/network usage fits the credit, then use the common setup. A paid billing upgrade permits charges beyond credits; do not confuse a larger trial-funded VM with the ongoing free VM offer.

[Official Google trial, eligibility and free limits](https://docs.cloud.google.com/free/docs/free-cloud-features).

**Azure:** eligible full-time university students can obtain $100 usable within 12 months without a credit card. Eligible general free-account users get $200 for 30 days. Verify the subscription's permitted VM sizes/regions and balance. Create a 4–8 GiB Ubuntu x86 VM within credits, attach persistent disk, configure networking/HTTPS and use the common setup. Track the VM, disk and public-address costs together. Student eligibility does not make an arbitrarily sized VM free indefinitely.

[Azure Students](https://azure.microsoft.com/en-us/free/students/), [general trial and spending behavior](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/avoid-charges-free-account).

## 7. Railway, Koyeb, Fly.io and static hosts

- **Railway:** its published Free limits are 1 GB RAM during the trial and 0.5 GB afterward, with limited credits/storage. Do not spend time deploying this complete backend there on Free. A sufficiently provisioned paid service would need Docker, a persistent volume, a stable JWT secret and `PORT` mapped to `MAI_PORT`.
- **Koyeb:** its free instance has 512 MB RAM, 0.1 vCPU, 2 GB SSD and no persistent volumes. It does not fit the full pipeline. A paid suitably sized service needs the same container/storage work.
- **Fly.io:** the trial provides 2 total VM hours or seven days, with up to 4 GB RAM; trial machines automatically stop after five minutes. This is not a reliable presentation host for a long analysis. Normal hosting needs a container, suitable machine RAM and persistent volume, with usage billing after the trial.
- **Cloudflare Pages / Vercel Hobby / Render Static:** deploy only the built frontend and connect to a suitable backend using `VITE_API_URL` and `MAI_ALLOWED_ORIGINS` as above. Vercel Hobby is restricted to personal/noncommercial use. A static deployment by itself cannot transcribe audio.
- **AWS Lambda / Cloud Run / similar request-driven compute:** free quotas do not make the present background-thread/SQLite/filesystem architecture a direct fit. Durable external jobs and storage, lifecycle changes and measurements would be needed. This is more work than the single-VM route.
- **A university/lab server:** if available with permission and enough RAM/disk, it can run the same single-server setup without a separate cloud compute bill.

[Railway](https://railway.com/pricing), [Koyeb](https://www.koyeb.com/docs/reference/instances), [Fly trial](https://docs.fly.io/about/free-trial), [Pages Free limits](https://developers.cloudflare.com/pages/platform/limits/), [Vercel Hobby use](https://vercel.com/docs/limits/fair-use-guidelines).

## Common Ubuntu x86 VM setup

These are setup instructions, not commands already run on a remote VM. First transfer reviewed source into `~/meetiq`. Include `backend/`, `src/`, `config/config.yaml`, `environment/`, `scripts/`, `deployment/`, frontend source/lockfiles and the trusted trained artifact `models/discussion/model.joblib`. Provision pretrained models with the scripts. Keep Android builds, virtual environments, private recordings, real credentials and account databases out of public source/image repositories.

Install Python 3 with venv support, FFmpeg/ffprobe, Git and a compatible Node/npm first. The checked frontend Vite package requires Node `^20.19.0 || >=22.12.0`; use a supported Node release satisfying that constraint. Do not assume an Ubuntu distribution's default Node version is recent enough.

```bash
cd ~/meetiq
bash scripts/setup.sh
.venv/bin/python scripts/download_models.py --asr-model small --slides
.venv/bin/python scripts/download_speaker_models.py
.venv/bin/python scripts/validate_setup.py
```

Inspect the printed model readiness, not just the exit code. Speech, slide embeddings and diarization must all be ready for the complete demo. `setup.sh` builds the frontend. Rebuild it after any frontend source/environment change.

Start privately:

```bash
MAI_PORT=8000 MAI_ASR_MODEL=small MAI_ASR_DEVICE=cpu MAI_ASR_COMPUTE_TYPE=int8 bash deployment/run_workstation.sh
```

The launcher defaults to loopback and closed registration. For a fresh database, briefly enable registration while the server is private, use an SSH port forward to create the intended account, then restart with `MAI_ALLOW_REGISTRATION=0` before publishing. Do not overwrite or migrate the existing laptop's private account data without an explicit decision.

For a lasting server, run this same launcher under systemd with the correct user, project working directory and environment, and restart-on-failure. Put a TLS reverse proxy in front; `deployment/Caddyfile.example` is a starting template needing your actual hostname/DNS. A temporary tunnel is also possible for a demo. Use one API process, not multiple writable replicas or `uvicorn --workers N`.

### State that must survive

- `data/state/nexus_v2.db`: account and meeting records.
- `.runtime/jwt-secret`, or a stable `MAI_SECRET_KEY` stored privately: token signing.
- `.runtime/uploads` and `.runtime/jobs`: uploaded files and resumable job state.
- `data/custom_test`, `data/processed`, `outputs/reports`: inputs, processed artifacts and reports as used by the pipeline.
- Required model/config files and their versions.

The API has `MAI_DB_PATH`, `MAI_RUNTIME_DIR` and `MAI_DATA_DIR` overrides, but processed/report paths also derive from the project root/configuration. Setting only one `/data` variable is insufficient. On a VM, keeping the application working directory and its state on persistent storage is simplest. In a container, explicitly mount or redirect every required state path. Do not bake users' recordings into the image.

### Deployment acceptance check

1. Open the HTTPS URL from another network; check `/api/health`, speech and diarization readiness.
2. Create the intended account privately, then check login/logout after publishing.
3. Analyze two short audio parts with two presentation files; check cumulative progress, final transcript, speakers, slide alignment, influence and export.
4. Reload the page, log in again, and confirm the report and source media remain accessible.
5. Restart the server and repeat the saved-history check. A live job's interrupted/recovery behavior also needs verification on the selected provider.
6. Measure a fresh processing run including upload/queue time on the selected machine. Local timing does not certify cloud timing.

No provider-specific deployment, ARM installation, cloud benchmark, remote restart test or account entitlement check was performed while preparing this comparison. Default ephemeral disks and expired credits can remove access to saved data; back up important results before relying on any trial host.
