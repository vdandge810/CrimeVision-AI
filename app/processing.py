import hashlib, json, os, mimetypes
from pathlib import Path
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def classify_media(filename: str, content_type: str | None) -> str:
    ct = (content_type or mimetypes.guess_type(filename)[0] or "").lower()
    ext = Path(filename).suffix.lower()
    if ct.startswith("image/") or ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}:
        return "image"
    if ct.startswith("video/") or ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "video"
    if ct.startswith("audio/") or ext in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}:
        return "audio"
    return "other"

def process_evidence(path: Path, media_type: str) -> dict:
    result = {
        "processed_at": utc_now(),
        "media_type": media_type,
        "status": "completed_with_limitations",
        "observations": [],
        "transcript": None,
        "model_notes": []
    }
    if media_type in ("image", "video"):
        try:
            from ultralytics import YOLO
            model_path = os.getenv("YOLO_MODEL_PATH", "").strip() or "yolo11n.pt"
            model = YOLO(model_path)
            if media_type == "image":
                predictions = model(str(path), verbose=False)
                result["observations"] = _yolo_observations(predictions)
            else:
                # Sample at most 1 frame per second for this MVP.
                import cv2
                cap = cv2.VideoCapture(str(path))
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                duration = frame_count / fps if fps else 0
                sample_times = list(range(0, min(int(duration) + 1, 301), 1))
                observations = []
                for sec in sample_times:
                    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
                    ok, frame = cap.read()
                    if not ok:
                        continue
                    preds = model(frame, verbose=False)
                    for item in _yolo_observations(preds):
                        item["timestamp_seconds"] = sec
                        observations.append(item)
                cap.release()
                result["observations"] = observations
                result["video_duration_seconds"] = round(duration, 2)
            result["model_notes"].append("Generic object detection only; model labels and confidence are not forensic conclusions.")
        except ImportError:
            result["status"] = "uploaded_not_processed"
            result["model_notes"].append("Optional dependency 'ultralytics' is not installed; no object detection was run.")
        except Exception as e:
            result["status"] = "processing_error"
            result["model_notes"].append(f"Object detection could not complete: {type(e).__name__}: {e}")
    elif media_type == "audio":
        try:
            import whisper
            model = whisper.load_model("base")
            transcribed = model.transcribe(str(path))
            result["transcript"] = transcribed.get("text", "").strip()
            result["segments"] = [
                {"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "").strip()}
                for s in transcribed.get("segments", [])
            ]
            result["model_notes"].append("Automated speech transcription may mishear names, words, timing, or speakers.")
        except ImportError:
            result["status"] = "uploaded_not_processed"
            result["model_notes"].append("Optional dependency 'openai-whisper' is not installed; no transcription was run.")
        except Exception as e:
            result["status"] = "processing_error"
            result["model_notes"].append(f"Audio transcription could not complete: {type(e).__name__}: {e}")
    else:
        result["status"] = "uploaded_not_processed"
        result["model_notes"].append("Unsupported media type; file was stored and hashed, but not analyzed.")
    return result

def _yolo_observations(predictions):
    observations = []
    for pred in predictions:
        names = getattr(pred, "names", {})
        boxes = getattr(pred, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = [round(float(v), 2) for v in box.xyxy[0].tolist()]
            observations.append({
                "label": str(names.get(cls_id, cls_id)),
                "confidence": round(conf, 4),
                "bbox_xyxy": xyxy
            })
    return observations
