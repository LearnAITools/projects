# AI YouTube Video Automation Pipeline

A complete, production-quality automated pipeline for creating and publishing AI-generated YouTube videos.

## Phase 1: Project Foundation ✅

This is the initial foundation phase. The project structure, configuration system, and logging are now in place.

### Features Implemented

- **Clean Project Structure**: Modular organization with separate packages for each concern (content, images, audio, video, youtube, pipeline)
- **Configuration Management**: Environment-based settings using Pydantic
- **Logging System**: Structured logging with console and optional file output
- **File Management**: Utilities for managing generated assets
- **Error Handling**: Comprehensive exception handling and logging

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
AI YouTube Pipeline - Foundation Phase
============================================================
Environment: development
Log Level: INFO
Dry Run: true
Data Directory: data
Data directory ready: data
============================================================
Foundation phase initialized successfully!
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
```

## Testing

Run the application to verify everything is working:

```bash
python -m app.main
```

## Next Steps

Phase 1 is complete. When ready, proceed to **Phase 2: Claude Content Generation**.

This will implement:
- Claude API integration
- Content generation for a given topic
- Structured JSON output (title, script, scenes, YouTube metadata)
- Response validation

Confirm when you want to proceed to Phase 2.

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

Created: 2026-08-30 | Phase: Foundation (1/7)
