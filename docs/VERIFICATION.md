# Verification report — 10 October 2026

Implementation location: `C:\Users\link4\OneDrive\Desktop\Use Case 3` (the registered project). The projectless chat directory was not used as a substitute repository. Master prompt, guide, all policies, all CSV schemas/rows and evaluation inputs were inspected before implementation. No external credentials were supplied or invented.

## Implemented

- Next.js **JavaScript** App Router/Tailwind UI: landing, Email/Password registration/sign-in, Google sign-in, protected overview, incident/follow-up conversation, policy search and full text, analytics, escalations, history/detail, and Manager CSV Data Update. Navy sidebar/light surfaces/purple actions; responsive CSS and accessible form labels/status messages.
- Express/Firebase Admin ID-token verification, default Employee profiles, trusted Manager bootstrap, Mongoose case/profile/upload/audit models and initialized indexes, own-case resource scoping, manager status changes, request validation, rate limits, upload caps, safe errors/logging, private Python calls.
- FastAPI/Pydantic safety/triage/retrieval/data/workflow/answer/final-validation pipeline. Two distinct Groq LLM roles; deterministic tools are not described as autonomous agents. Missing/invalid provider responses are explicitly unavailable. Final recommendations are exact validated policy excerpts; numeric findings come from pandas.
- Configurable OpenAI-compatible embeddings contract, dimension verification, Pinecone REST integration, explicit index creation command, idempotent chunk IDs and corpus/config namespaces, readiness verification before publishing ingestion metadata.
- All nine inspected CSV datasets: allowlist, UTF-8/schema/type/date/key/reference validation, immutable staging and failed-upload records, safe preview/comparison, checksum verification, explicit activation, revision conflict checks, atomic manifest, audit history, restart persistence, rollback, quota, and isolated originals. Uploaded employee/escalation records never grant permissions or change governing policy.
- Evaluation runner respecting the supplied schema dictionary; unique output directories; Dockerfiles, five-service Compose, Caddy TLS config, least-privilege Mongo app user, read-only original mounts, volumes, health checks, README and source decision notes.

## Exact checks and observed results

Commands are relative to the indicated project subdirectory. Windows commands used the venv in `work/venv`.

| Directory | Command | Observed result |
|---|---|---|
| root | `python scripts\inspect_sources.py` | Parsed all nine CSVs; **19/19 original SHA-256 hashes unchanged**, verified again after implementation |
| ai-service | `..\work\venv\Scripts\python -m pytest -q` | **47 passed**, zero failures/skips; 7 dependency deprecation warnings (Starlette httpx compatibility and pandas/NumPy timedelta handling) |
| api | `npm run check` | JavaScript syntax checks passed |
| api | `npm test` | **14 passed**, zero failures/skips: nine auth/validation tests plus five real service/database integration tests |
| web | `npm run lint` | Exit 0, no errors or warnings |
| web | `npm run build` | Next.js **16.4.0** production build passed; landing, auth, seven workspace pages, incident detail, and not-found output generated |
| web | `npm start` | Standalone production server started locally on loopback; browser navigation/guard behavior inspected |
| root | `.\work\docker-compose.exe --env-file .env.example config --quiet` | Exit 0 using downloaded official Compose **v5.6.0**; services: ai, mongo, api, web, proxy |
| root | `work\venv\Scripts\python scripts\analytics_report.py` | Actual-source deterministic outputs saved to `data/generated/verified-analytics.json` |
| ai-service | `..\work\venv\Scripts\python -m app.evaluate` | All **11** public cases processed, **0 skipped**, 1 deterministic safety completion, **10 explicitly unavailable** due to missing AI configuration |
| ai-service | `..\work\venv\Scripts\python -m app.ingest` | Exit 1, `Embedding provider/model is not configured`; **no index ingestion claimed** |
| api | `npm audit --omit=dev` | **0 vulnerabilities** in production dependency audit; full API audit also clean after Firebase Admin update |
| web | `npm audit --omit=dev` | **0 vulnerabilities** in production dependency audit after patched gRPC override |
| web | `npm audit` | **5 high-severity development-tool dependency findings remain**, in eslint-config-next → glob/micromatch/braces; registry's available latest braces was 3.0.3, still affected. No unsafe framework downgrade applied |
| source directories | `rg` credential-pattern scan (Groq/Pinecone/Google-key/private-key signatures) | No matches; only `.env.example` exists at root. This is a scoped scan, not proof of absence of every possible secret |

The Next build prints its generic “Running TypeScript” check stage; the application source is JS/JSX, with no authored TypeScript. Lockfiles preserve the installed versions. Python dependencies are in `requirements.lock.txt` and installed in the production Dockerfile.

## What the integration tests actually exercised

The tests started a real MongoDB **8.0.14** binary on an ephemeral local port and a real Uvicorn/FastAPI process on `127.0.0.1:18081`. Express used the actual HTTP Python adapter and Mongoose models. They verified policy retrieval from disk, pandas results, security-refusal persistence, request-key idempotency, own-case visibility, manager status changes, masked unavailable-case persistence, manager upload metadata, immutable staging, activation, version-tagged analytics, rollback, failed validation and Employee denial at both Node and Python boundaries.

Firebase identity verification was **injected only inside the test process**, so these are not live Firebase token/provider tests. There is no production bypass. LLM unit tests use explicit test doubles for valid/malformed output and fabricated citations; they are not live Groq/Pinecone integration evidence.

Two actual failures were corrected before the final pass: CRLF/LF inconsistency in chunk membership checks, and Mongoose attempting automatic collection/index initialization before database connection. The latter was fixed by explicit post-connection initialization in both server and bootstrap paths.

## Browser checks

The local production web server was opened through the Codex browser. Verified landing content and Get Started navigation; registration identifies Employee and has no Manager selector; Firebase-unconfigured messaging is visible; direct `/data` access when signed out presents the protected sign-in state. Tested a 390 × 844 viewport (document width remained 390, with no horizontal overflow) and a 1440-pixel desktop viewport. Local screenshot saved with the final deliverables.

**Not browser-verified:** a real signed-in Employee/Manager session, Google OAuth flow, or authenticated page interactions, because no Firebase project configuration/credentials were provided. The backend actions were exercised in the real local service tests described above. Responsive authenticated layouts are implemented but were not inspected in a live authorized browser session.

## Actual evaluation results

Final run: `data/generated/evaluation-20261010T084547101188Z/`.

| Measurement | Result | Interpretation |
|---|---:|---|
| Public sample size | 11 | Every row processed |
| Completed deterministic safety refusal | 1 | PUB-008; does not require provider keys |
| AI unavailable | 10 | Recorded as failures, not silently skipped |
| Category accuracy over all cases | 1/11 = **9.09%** | Unavailable cases count as incorrect |
| Priority accuracy over all cases | 1/11 = **9.09%** | Unavailable cases count as incorrect |
| Citation presence over all cases | 1/11 = **9.09%** | Real citations on deterministic security refusal |
| Expected-reference recall | 2/17 = **11.76%** | Literal expected-source overlap, not semantic relevance |
| Public refusal/masking checks | 2/2 = **100%** | PUB-008 refusal, PUB-009 masking even in unavailable state; narrow checks, not overall safety certification |
| Data-answer correctness metric | **Not measured** | No machine-readable numeric gold answers supplied; deterministic checks and traceable report provided instead |
| Skipped cases | 0 | Exceptions/unavailability are explicit |

Latency values in `report.json` measure this unconfigured local run, not live model latency. Confidence 0 in exported predictions is a documented sentinel when no model estimate exists. The guide's 75%/85% targets were **not achieved** in this unconfigured run; no live model performance claim is made.

## Actual-source analytical results

- 21 unresolved P1/P2 support records in the anchored last 24 hours.
- 205 short receipt records, totaling 3,304 missing units, in the last 30-day receipt window.
- ST002 / SKU1001 (English Willow Cricket Bat): on-hand 0; seeded latest receipts 18/50 and 20/45; V001 fill rate 0.68. These support investigation of repeated short deliveries.
- ST005 / SKU7001 (Tennis Ball Pack): store and WH001 warehouse on-hand 0, supporting warehouse depletion as a likely cause.
- Thirty-day quality view's highest associated record count: V007 ActiveFit Machines, 7 support complaint records + 10 quality-return records = 17 associated records. These cannot be deduplicated into unique complaints; no fault is assigned.

## Required configuration and external setup

Fill these values before real sign-in/AI testing:

- Browser Firebase: `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`, `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`, plus `NEXT_PUBLIC_API_URL` for local API origin. Rebuild after changing public values.
- Firebase Admin: `GOOGLE_CLOUD_PROJECT`; `GOOGLE_APPLICATION_CREDENTIALS` path or valid ADC. Compose uses `FIREBASE_ADMIN_FILE` secret. Enable Email/Password and Google providers; configure authorized hostnames; register and bootstrap the intended first Manager UID.
- Persistence/private API: `MONGODB_URI`, `INTERNAL_SERVICE_SECRET` (random ≥32 characters), `PYTHON_URL`, `ALLOWED_ORIGINS`; Compose additionally needs distinct `MONGO_ROOT_PASSWORD` and `MONGO_APP_PASSWORD`. No persistent production Mongo instance was provisioned.
- Groq: `GROQ_API_KEY`, **`GROQ_MODEL` exact supported Llama 3.3 model ID**. The example model placeholder is intentionally non-working.
- Embeddings: **choose** `EMBEDDING_PROVIDER=openai-compatible`, exact/versioned `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`. No provider or model was silently selected.
- Pinecone: `PINECONE_API_KEY`, `PINECONE_INDEX`; set `PINECONE_CLOUD`, `PINECONE_REGION`, `PINECONE_METRIC` when creating. Dimension is measured from embeddings; optional `PINECONE_DIMENSION` asserts it. Create if absent, ingest, verify retrieval, then re-run evaluation.
- VPS: Docker Engine, domain DNS, `DOMAIN`, HTTPS allowed origin, firewall/SSH restrictions, secret files, backups and monitoring. Compose was syntax/config validated only. **No Docker image build/container run or VPS deployment was performed**, because the machine has no Docker Engine/CLI installation; only standalone Compose was obtained for config validation.

## Remaining limitations

Exact-excerpt selection limits unsupported policy wording but cannot guarantee relevance; masking/injection patterns cannot recognize every attack or sensitive value. Confidence is not calibrated. Incident transcripts can still contain unrecognized personal information. Humans retain consequential decisions.

No POS/ERP/payment/vendor/ticket-notification integrations exist. There is no real-time stock feed, local embedding model, multi-dataset atomic transaction, distributed filesystem/Mongo transaction, or multi-replica shared-state deployment. Filesystem manifest audit is authoritative if a mutation completes but the Mongo mirror write fails. Source role/escalation CSV uploads do not redefine access or policy. Storage retains every version until an administrator performs a separately reviewed archival operation. Live authentication, index creation/ingestion, model calls, authenticated UI smoke, container execution, TLS and VPS remain unverified.

No source file was modified: the final integrity check passed for all 19 originals. No Git repository/commit was created; no claim of committed-secret scanning is made. All code was written into the actual registered project folder. See README for full commands, backup/restore guidance, API contract and the supplied-case demo script.
