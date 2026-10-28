# CrimeVision AI — Starter Project Package

An educational MVP for multimodal evidence organization and forensic decision support. It provides:
- Evidence upload for images, videos, and audio
- SHA-256 hashing of original uploads and a basic evidence register
- Optional YOLO object detection for images/video (requires model weights/dependencies)
- Optional Whisper transcription for audio
- A chronological event/timeline view
- Evidence-grounded chat over the case's stored metadata and processing results
- PDF case report generation
- A simple browser dashboard

## Important limitations
This is a starter implementation, not a validated forensic product. AI detections/transcripts can be wrong and must be reviewed by qualified personnel. Do not use generated outputs as proof or as the sole basis for law-enforcement decisions. Preserve original files, document chain of custody, restrict access, and follow applicable law and institutional policies. This MVP does not provide tamper-proof custody, user authentication, encryption-at-rest, or validated forensic acquisition.

## Requirements
- Python 3.10+ recommended
- 8 GB RAM minimum; 16 GB recommended
- FFmpeg is recommended for Whisper audio/video support
- Optional: GPU for faster model inference

## Quick start
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

The first run creates `data/` and a SQLite database. Upload sample media only if you have the right to process it.

## Optional AI components
- Object detection: install `ultralytics`; the default YOLO model may download weights on first use. For a controlled/offline setup, provide an approved local model path via `YOLO_MODEL_PATH`.
- Audio transcription: install `openai-whisper` and make sure FFmpeg is installed.
- AI models are optional. If missing, uploads and case management still work, and processing status will explain what is unavailable.

## Project structure
```text
CrimeVision_AI/
  app/
    main.py          FastAPI routes
    database.py      SQLite persistence
    processing.py    Hashing, optional vision/audio processing
    reporting.py     PDF report generator
    static/index.html Dashboard
  data/              Created at runtime
  requirements.txt
  .env.example
```

## Main API routes
- `GET /api/health`
- `GET /api/evidence`
- `POST /api/evidence` (multipart form: `file`, optional `case_id`, `notes`)
- `POST /api/evidence/{evidence_id}/process`
- `GET /api/timeline`
- `POST /api/chat`
- `GET /api/report.pdf`

## Suggested development roadmap
1. Establish requirements, consent/legal basis, evidence handling policy, and threat model.
2. Add login, role-based access control, audit logs, encrypted storage, and retention controls.
3. Add immutable/append-only chain-of-custody records and verified timestamps.
4. Add robust video frame sampling, audio/video synchronization, and confidence calibration.
5. Add evidence-grounded RAG with source citations and explicit “not found in evidence” responses.
6. Validate models on representative datasets and report false-positive/false-negative rates.
7. Add tests, Docker deployment, monitoring, backups, and security review.

## Troubleshooting
- If `python-multipart` is missing, activate the virtual environment and run `pip install -r requirements.txt`.
- Whisper may fail without FFmpeg; install it and restart the terminal.
- YOLO may require internet access to fetch default weights. Set `YOLO_MODEL_PATH` to a local model file if needed.


## Professional UI upgrade

This package includes a redesigned responsive investigation dashboard and a SHA-256 integrity recheck endpoint. The interface provides a more realistic case-workspace aesthetic while keeping the existing FastAPI analysis workflow.

### Start the app
Open PowerShell in the folder containing `requirements.txt`, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. For a new project copy, keep the original `CrimeVision_AI` folder as a backup before replacing it.
