import json, os, uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .database import init_db, connect, UPLOAD_DIR
from .processing import sha256_file, classify_media, process_evidence, utc_now
from .reporting import make_report

BASE_DIR = Path(__file__).resolve().parent.parent
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
ALLOWED_EXTS = {".jpg",".jpeg",".png",".bmp",".webp",".tiff",".mp4",".mov",".avi",".mkv",".webm",
                ".wav",".mp3",".m4a",".aac",".ogg",".flac"}

app = FastAPI(title="CrimeVision AI", version="0.1.0",
              description="Educational multimodal evidence review MVP")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "app" / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"status":"ok", "app":"CrimeVision AI", "version":"0.1.0"}

def row_dict(row):
    d = dict(row)
    try: d["results"] = json.loads(d.pop("results_json", "{}"))
    except Exception: d["results"] = {}
    return d

@app.get("/api/evidence")
def list_evidence(case_id: str | None = None):
    with connect() as con:
        if case_id:
            rows = con.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM evidence ORDER BY id DESC").fetchall()
    return [row_dict(r) for r in rows]

@app.post("/api/evidence")
async def upload_evidence(file: UploadFile = File(...), case_id: str = Form("CASE-001"), notes: str = Form("")):
    original_name = Path(file.filename or "upload.bin").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, "Unsupported file extension.")
    if not case_id.strip() or len(case_id) > 100:
        raise HTTPException(400, "case_id must be 1–100 characters.")
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if not payload:
        raise HTTPException(400, "Empty upload.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_BYTES} bytes.")
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / stored_name
    path.write_bytes(payload)
    digest = sha256_file(path)
    media_type = classify_media(original_name, file.content_type)
    with connect() as con:
        cur = con.execute("""
        INSERT INTO evidence(case_id,filename,stored_name,media_type,size_bytes,sha256,uploaded_at,notes)
        VALUES(?,?,?,?,?,?,?,?)""",
        (case_id.strip(), original_name, stored_name, media_type, len(payload), digest, utc_now(), notes[:2000]))
        evidence_id = cur.lastrowid
        con.commit()
    return {"id": evidence_id, "case_id":case_id.strip(), "filename":original_name,
            "media_type":media_type, "size_bytes":len(payload), "sha256":digest,
            "processing_status":"pending", "message":"Uploaded and hashed. Processing has not run yet."}

@app.post("/api/evidence/{evidence_id}/process")
def process_one(evidence_id: int):
    with connect() as con:
        row = con.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        if not row: raise HTTPException(404, "Evidence not found.")
        item = dict(row)
        path = UPLOAD_DIR / item["stored_name"]
        if not path.exists(): raise HTTPException(410, "Stored file is missing.")
        result = process_evidence(path, item["media_type"])
        con.execute("UPDATE evidence SET processing_status=?, results_json=? WHERE id=?",
                    (result["status"], json.dumps(result), evidence_id))
        # Store only coarse, model-generated events; human review remains necessary.
        if result.get("observations"):
            for obs in result["observations"]:
                timestamp = f"{obs.get('timestamp_seconds', 0)}s" if item["media_type"] == "video" else "time not available"
                desc = f"Model detected label '{obs.get('label','unknown')}' at {timestamp}; confidence {obs.get('confidence',0):.3f}. Verify manually."
                con.execute("""INSERT INTO events(case_id,evidence_id,event_time,event_type,description,confidence,source)
                               VALUES(?,?,?,?,?,?,?)""",
                            (item["case_id"], evidence_id, timestamp, "AI observation", desc,
                             obs.get("confidence"), "automated model"))
        if result.get("transcript"):
            for seg in result.get("segments", []):
                ts = f"{seg.get('start',0):.2f}s"
                desc = f"Automated transcript: {seg.get('text','')}"
                con.execute("""INSERT INTO events(case_id,evidence_id,event_time,event_type,description,confidence,source)
                               VALUES(?,?,?,?,?,?,?)""",
                            (item["case_id"], evidence_id, ts, "Audio transcript", desc, None, "Whisper; verify manually"))
        con.commit()
    return {"evidence_id": evidence_id, "results": result}

@app.get("/api/timeline")
def timeline(case_id: str | None = None):
    with connect() as con:
        if case_id:
            rows = con.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM events ORDER BY id").fetchall()
    return [dict(r) for r in rows]

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    case_id: str = "CASE-001"

@app.post("/api/chat")
def chat(req: ChatRequest):
    q = req.question.lower()
    with connect() as con:
        evidence = con.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (req.case_id,)).fetchall()
        events = con.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (req.case_id,)).fetchall()
    if not evidence:
        answer = f"No evidence is registered for case {req.case_id}. Upload evidence first."
    elif any(term in q for term in ("hash", "sha", "integrity")):
        answer = "Registered file hashes (SHA-256):\n" + "\n".join(f"Evidence {r['id']} — {r['filename']}: {r['sha256']}" for r in evidence)
    elif any(term in q for term in ("timeline", "when", "sequence", "event")):
        answer = "Recorded events (not necessarily a complete or synchronized chronology):\n" + (
            "\n".join(f"{e['event_time']} — {e['event_type']}: {e['description']}" for e in events)
            if events else "No events have been recorded. Process available evidence first."
        )
    elif any(term in q for term in ("audio", "transcript", "said", "speech", "witness")):
        found = []
        for r in evidence:
            try:
                data = json.loads(r["results_json"] or "{}")
                if data.get("transcript"):
                    found.append(f"Evidence {r['id']} ({r['filename']}): {data['transcript']}")
            except Exception: pass
        answer = "\n".join(found) if found else "No audio transcript is available in the stored processing results. Install/configure Whisper and process an audio file."
    elif any(term in q for term in ("object", "person", "weapon", "detected", "image", "video")):
        found = []
        for r in evidence:
            try:
                data = json.loads(r["results_json"] or "{}")
                labels = [o.get("label","unknown") for o in data.get("observations",[])]
                found.append(f"Evidence {r['id']} ({r['filename']}): {', '.join(labels) if labels else 'no stored detections'}")
            except Exception: pass
        answer = "\n".join(found) if found else "No detection results are available yet. Process the evidence first."
        answer += "\nNote: generic object labels do not establish identity, intent, or whether an object is a weapon."
    else:
        answer = "Case evidence register:\n" + "\n".join(
            f"ID {r['id']}: {r['filename']} | type={r['media_type']} | status={r['processing_status']} | notes={r['notes'] or 'none'}"
            for r in evidence
        ) + "\nAsk about hashes, timeline/events, transcripts, or object detections for a more focused answer."
    return {"case_id": req.case_id, "question": req.question, "answer": answer,
            "grounding": "Response is derived from stored case records only; no external facts inferred."}



@app.post("/api/evidence/{evidence_id}/verify")
def verify_evidence(evidence_id: int):
    """Recalculate SHA-256 and compare with the hash recorded at upload."""
    with connect() as con:
        row = con.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Evidence not found.")
    item = dict(row)
    path = UPLOAD_DIR / item["stored_name"]
    if not path.is_file():
        return {"evidence_id": evidence_id, "exists": False, "match": False,
                "recorded_sha256": item["sha256"], "current_sha256": None}
    current = sha256_file(path)
    return {"evidence_id": evidence_id, "exists": True,
            "match": current == item["sha256"],
            "recorded_sha256": item["sha256"], "current_sha256": current}

@app.get("/api/report.pdf")
def report(case_id: str = "CASE-001"):
    with connect() as con:
        evidence = con.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
        events = con.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (case_id,)).fetchall()
    pdf = make_report([dict(r) for r in evidence], [dict(r) for r in events], case_id)
    return StreamingResponse(pdf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="crimevision_{case_id}.pdf"'})
