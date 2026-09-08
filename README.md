# AI YouTube Video Automation Pipeline

A complete, production-quality automated pipeline for creating and publishing AI-generated YouTube videos.

## Current Status: Phase 20 - Upload Lifecycle Integration ✅

The project now includes the content-to-video pipeline, scheduled automation, and restart-safe operational state tracking.

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

- Python 3.8 or higher
- pip or conda

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

# Edit .env with your actual API keys (you'll add these in later phases)
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

# API Keys (to be added in later phases)
CLAUDE_API_KEY=                  # Phase 2
IMAGE_API_KEY=                   # Phase 3
IMAGE_PROVIDER=
VOICE_API_KEY=                   # Phase 4
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

The next increment should add durable scheduling or notifications around completed and failed jobs.

## Development Rules

- Keep modules small and focused
- Use meaningful names
- Never hardcode secrets
- Use type hints
- Add docstrings to public functions
- Handle API failures properly
- Keep external providers behind abstractions
- Write testable code

## Project Goals

The complete pipeline will support:
1. ✅ **Phase 1**: Project foundation (COMPLETE)
2. **Phase 2**: Claude content generation
3. **Phase 3**: Image generation with provider abstraction
4. **Phase 4**: AI voice / voice cloning
5. **Phase 5**: Video creation and composition
6. **Phase 6**: YouTube API integration
7. **Phase 7**: Complete pipeline orchestration

With support for:
- Job management and state tracking
- Intelligent caching (avoid regenerating existing assets)
- Cost control (skip unnecessary API calls)
- Comprehensive error handling and retry logic
- Detailed logging and monitoring
- Scheduled execution and batch processing

---

Created: 2026-08-30 | Current phase: Upload lifecycle integration (20)
