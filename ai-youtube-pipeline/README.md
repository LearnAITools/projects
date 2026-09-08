# AI YouTube Video Automation Pipeline

An actively developed pipeline for generating and publishing AI-assisted YouTube videos.

## Current Status: Phase 37 - Production-Readiness Prototype ✅

The project has a working, tested path from topic to content, selectable long-form or Short output, media generation, MP4 composition, metadata, persisted scheduling and job state, optional scheduled YouTube upload, notifications, recovery, quality checks, and operator controls. It is still a production-readiness prototype: live provider credentials, real-account OAuth, deployment behavior, and unattended publishing need operational validation.

### Verified Baseline

- `119` automated tests pass with `python -m pytest -q`.
- Content generation uses the Claude API when `CLAUDE_API_KEY` is configured.
- Image generation supports a configurable HTTP provider and a local placeholder provider.
- Narration supports a configurable HTTP provider and a local placeholder provider.
- Video composition uses the local `ffmpeg` executable.
- YouTube upload is protected by `DRY_RUN=true` by default; real upload requires OAuth credentials and a first-run browser authorization.
- Notifications support durable local delivery with a console delegate; external channels still need configuration and live validation.

The test suite validates interfaces, state transitions, caching, format constraints, rendering, provider adapters, scheduling, retries, upload recovery, notifications, observability, quality controls, persistence, worker controls, and cost limits. It does not prove third-party provider quality, live OAuth in a real account, or long-running deployment behavior.

### Features Implemented

- **Clean Project Structure**: Modular organization with separate packages for each concern (content, images, audio, video, youtube, pipeline)
- **Configuration Management**: Environment-based settings using Pydantic
- **Logging System**: Structured logging with console and optional file output
- **File Management**: Utilities for managing generated assets
- **Error Handling**: Comprehensive exception handling and logging
- **Restart Safety**: Existing media outputs are reused and video composition receives cached stage outputs
- **Failure Diagnostics**: Failed jobs persist their stage and error in `job_state.json`
- **Operational CLI**: Run health checks or one scheduler pass from the command line
- **Job Monitoring**: Inspect aggregate status or one persisted job without mutation
- **YouTube Uploads**: Opt-in OAuth authentication and resumable video uploads
- **Upload Lifecycle**: Successful uploads persist video IDs and URLs in job state
- **Job Notifications**: Completion and failure events use an injectable notifier interface with a console implementation
- **Video Formats**: Jobs accept `LONG_FORM` or `SHORT`, persist the selection, and include format-specific rendering metadata
- **Format-Aware Rendering**: Long-form videos render at `1280x720`; Shorts render vertically at `1080x1920` and must remain below 180 seconds
- **Provider Adapters**: Configurable HTTP image and voice providers include validation and retry handling, with local placeholders retained for development
- **Durable Operations**: SQLite persistence, atomic scheduling claims, retries, resumable upload state, durable notifications, observability, quality/approval checks, worker controls, and cost limits are implemented

### Project Structure

```
ai-youtube-pipeline/
├── app/
│   ├── main.py                    # Application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Configuration settings
│   ├── content/                   # Phase 2: Claude content generation
│   ├── images/                    # Phase 3: Image generation
│   ├── audio/                     # Phase 4: Voice generation
│   ├── video/                     # Phase 5: Video building
│   ├── youtube/                   # Phase 6: YouTube integration
│   ├── pipeline/                  # Phase 7: Orchestration
│   ├── automation/                # Phases 8-37: Scheduling, execution, recovery, monitoring, and workers
│   └── utils/
│       ├── logger.py              # Logging configuration
│       └── file_manager.py        # File operations
│
├── data/                          # Output directories for generated assets
│   ├── input/
│   ├── scripts/
│   ├── images/
│   ├── audio/
│   ├── videos/
│   └── completed/
│
├── tests/                         # Unit tests
├── .env                           # Environment variables (gitignored)
├── .env.example                   # Configuration template
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- pip or conda
- `ffmpeg` available on `PATH` for MP4 composition

On macOS, install ffmpeg with `brew install ffmpeg`. Pillow is also required by the image and video modules; add it to the environment if it is not already installed (`pip install Pillow`).

### 2. Create Virtual Environment

```bash
cd ai-youtube-pipeline

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy the example configuration
cp .env.example .env

# Edit .env with your actual API keys and provider settings
nano .env  # or use your preferred editor
```

### 5. Verify Installation

```bash
python -m app.main
```

Expected output:
```
============================================================
AI YouTube Pipeline - Production Automation
============================================================
Environment: development
Log Level: INFO
Dry Run: true
Data Directory: data
Data directory ready: data
============================================================
Production automation foundation initialized successfully!
============================================================
```

## Configuration

Edit `.env` to customize settings:

```env
# Application
ENVIRONMENT=development          # development or production
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
DRY_RUN=true                     # Set to false to enable YouTube upload

# File Paths
DATA_DIR=data                    # Where to store generated assets

# API Keys and providers
CLAUDE_API_KEY=                  # Required for live content generation
IMAGE_API_KEY=                   # Reserved for a provider implementation
IMAGE_PROVIDER=
VOICE_API_KEY=                   # Reserved for a provider implementation
VOICE_PROVIDER=
YOUTUBE_CLIENT_ID=               # Phase 6
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REDIRECT_URI=http://localhost:8080/oauth2callback
YOUTUBE_TOKEN_FILE=data/youtube_token.json
YOUTUBE_CATEGORY_ID=22
YOUTUBE_PRIVACY_STATUS=private
```

For personal use, keep `DRY_RUN=true` during testing. Set `DRY_RUN=false` only when
OAuth is configured and an actual upload is intentional; the default privacy status
is `private`.

The current CLI constructs the default scheduler without a schedule file, so schedules
created through the CLI are not yet a complete restart-safe production queue. Persisted
job history and per-job pipeline state are separate from that scheduling limitation.

## Testing

Run the application to verify everything is working:

```bash
python -m app.main
```

Run scheduled jobs once, optionally adding an immediate topic:

```bash
python -m app.main --run-once
python -m app.main --run-once --topic "5 AI tools developers should know"
python -m app.main --status
python -m app.main --status job_20260902_001
```

## Phase History

- ✅ Phases 1-7: Foundation, content, images, audio, video, YouTube abstraction, and orchestration
- ✅ Phases 8-15: Scheduling, topic selection, job execution, full automation, and automation runner
- ✅ Phase 16: Production hardening for cached outputs and persisted failure diagnostics
- ✅ Phase 17: Operational CLI for health checks and one-shot runs
- ✅ Phase 18: Read-only persisted job monitoring and status inspection
- ✅ Phase 19: OAuth-backed, resumable YouTube uploads with dry-run protection
- ✅ Phase 20: Upload results integrated into automation status and job history
- ✅ Phase 21: Completion and failure notifications with an injectable notifier interface
- ✅ Phases 22-25: Long-form/Short format selection, sub-3-minute validation, vertical rendering, and scheduled publishing
- ✅ Phases 26-29: HTTP media providers, durable execution, retry/recovery, and upload idempotency
- ✅ Phases 30-33: Durable notifications, observability, quality/approval controls, and integration smoke coverage
- ✅ Phases 34-37: Transactional persistence, worker controls, media enhancements, cost controls, and operations documentation

## Missing And Critical Next Stages

These are ordered by production risk rather than feature novelty. The core implementation
is present; the remaining work is qualification and deployment readiness.

### P0 - Required Before Real Automated Publishing

- **Live provider qualification**: Generic HTTP image and voice adapters are implemented, but each selected vendor still needs concrete request/response mapping, credentials, quota and cost verification, and live end-to-end testing.
- **Production dependency packaging**: Pillow is imported by the application but is not declared in `requirements.txt`; dependency pinning, CI installation, and clean-environment verification remain.
- **Live YouTube qualification**: OAuth and scheduled upload behavior are implemented and tested with mocks, but a real private-account upload and scheduled publish should be verified before public use.
- **Deployment hardening**: Local worker, SQLite/JSON persistence, health checks, and operations documentation exist, but backups, secret management, process supervision, retention, and an actual deployment environment remain.

### P1 - Required For Reliable Operations

- **External notification delivery**: Durable notification tracking is implemented, but email, Slack, or webhook delivery still needs to be selected, configured, and tested against a real endpoint.
- **Operational validation**: Observability, alerts, quality checks, approval state, and operator commands exist; they still need runbooks, thresholds, and a production rehearsal.
- **Live integration coverage**: Current integration tests use mocks and local tools. A credentialed staging test plan is still required for Claude, media providers, OAuth, YouTube scheduling, and notifications.

### P2 - Product And Scale Improvements

- Replace JSON history/schedules with a transactional database when multiple workers or high job volume is expected.
- Add a proper worker process, graceful shutdown, queue visibility, cancellation, and admin operations for retrying or pausing jobs.
- Add thumbnail generation, captions/subtitles, music/volume mixing, scene timing checks, and configurable video templates.
- Add deployment documentation, secret management, CI, dependency pinning/updates, backups, retention policies, and cost budgets.

## Current Limitations

- The default configuration remains development-safe: local placeholder media and `DRY_RUN=true`.
- HTTP media providers are generic adapters, not vendor-specific integrations.
- SQLite is suitable for a local/small deployment; high availability and multi-host coordination are not provided.
- Real YouTube OAuth and third-party provider behavior are covered by mocks/unit tests, not live service tests.
- No CI workflow or complete deployment environment is included yet.

## Development Rules

- Keep modules small and focused
- Use meaningful names
- Never hardcode secrets
- Use type hints
- Add docstrings to public functions
- Handle API failures properly
- Keep external providers behind abstractions
- Write testable code

## Project Progress

- ✅ **Phases 1-7**: Foundation, content, images, audio, video, YouTube abstraction, and orchestration
- ✅ **Phases 8-15**: Scheduling, topic selection, job execution, full automation, and continuous runner
- ✅ **Phase 16**: Cached outputs and persisted failure diagnostics
- ✅ **Phase 17**: Operational CLI for health checks and one-shot runs
- ✅ **Phase 18**: Read-only job monitoring and status inspection
- ✅ **Phase 19**: OAuth-backed, resumable YouTube uploads with dry-run protection
- ✅ **Phase 20**: Upload results integrated into automation status and job history
- ✅ **Phase 21**: Completion and failure notifications
- ✅ **Phases 22-25**: Video format model, CLI selection, Short constraints, vertical rendering, and scheduled publishing
- ✅ **Phases 26-29**: HTTP media providers, durable execution, retries, recovery, and upload idempotency
- ✅ **Phases 30-33**: Durable notifications, observability, quality/approval controls, and integration smoke coverage
- ✅ **Phases 34-37**: Transactional persistence, worker controls, media enhancements, cost controls, and operations documentation

The pipeline currently supports a tested production-readiness prototype with both video
formats, topic-driven generation, media providers, scheduled uploads, recovery controls,
quality gates, monitoring, and operator workflows. The next milestone is live-service
qualification and deployment hardening.

## Goal Coverage And WIP

The original goal is now implemented as a tested local pipeline: accept a topic, choose
long-form or Short output, generate content and metadata, create visuals and narration,
render the video, and upload it to YouTube immediately or at a requested future time.
The remaining WIP is production qualification, not the core workflow design.

### What Is In Place

- **Topic input**: A topic can be supplied with `python -m app.main --run-once --topic "..."`.
- **AI content generation**: Claude is called to produce a validated script, hook, scenes, and YouTube metadata.
- **Image stage**: Scene image files are created and cached through an `ImageProvider` abstraction.
- **Voice stage**: Narration files are created and cached through a `VoiceProvider` abstraction.
- **Video assembly**: Scene images and audio are composed into an MP4 using ffmpeg.
- **Title and description**: Claude output includes title, description, and tags, which are passed to the YouTube client.
- **YouTube integration**: OAuth-backed resumable upload support exists, with dry-run protection enabled by default.
- **Scheduling and publishing**: Recurring schedules, persisted `publish_at`, CLI schedule operations, timezone validation, and YouTube scheduled upload payloads are implemented.
- **State and monitoring**: Job state, failures, upload details, and basic status inspection are persisted and test-covered.
- **Operational controls**: SQLite persistence, job claims and leases, retry/recovery, upload idempotency, durable notifications, observability, approval, worker controls, and cost limits are implemented.

### Things Still To Be Implemented / WIP

- **Vendor-specific media integrations**: HTTP image and voice adapters exist, but a chosen production vendor still needs concrete API mapping, credential setup, quota/cost verification, and live testing.
- **Dependency packaging**: Pillow is imported but missing from `requirements.txt`; CI and a clean-environment install should be added.
- **Live YouTube verification**: Test one real private scheduled upload and verify OAuth refresh, publish time, and recovery behavior before enabling public uploads.
- **External notifications**: Durable local notification tracking exists, but an actual Slack, email, or webhook channel still needs to be selected and configured.
- **Deployment readiness**: Add process supervision, backups, secret management, retention, alert runbooks, and a real staging/production deployment.
- **Scale boundary**: SQLite is appropriate for local or small deployments; multi-host high availability and larger worker fleets need further architecture.
- **Test boundary**: The `119` tests use mocks/local tools for external services. Live-service qualification remains intentionally outside the automated suite.

### Current Recommendation

Keep `DRY_RUN=true` and `YOUTUBE_PRIVACY_STATUS=private` while completing provider,
dependency, staging, and deployment validation. Enable unattended public publishing only
after a real private scheduled-upload rehearsal succeeds.

---

Created: 2026-08-30 | Updated: 2026-09-04 | Current phase: Phase 37 prototype; live-service qualification and deployment hardening next
