"""
IndexTTS2 FastAPI Server
解耦架构：FastAPI 轻量启动，模型按需加载 → 生成 → 释放
参考 Qwen3-TTS WebUI 架构
"""
import os
import sys
import gc
import io
import base64
import logging
import warnings
import tempfile
import time
from pathlib import Path
from typing import Optional

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from mlx_indextts.generate_v2 import IndexTTSv2
except ImportError:
    print("Error: 'mlx-indextts' not found. Please run in ~/mlx-indextts with venv activated.")
    sys.exit(1)

# === CONFIG ===
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL_PATH = os.path.expanduser("~/.cache/indextts2/mlx-indextts2-standard-8bit")
DEFAULT_REF = os.path.expanduser("~/.cache/indextts2/snowball_voice.npz")

PORT = 7861

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# === FASTAPI APP ===
app = FastAPI(title="IndexTTS2 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# === MODELS ===
class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    emotion: str = Field("calm", description="calm/happy/sad/angry/afraid/disgusted/melancholic/surprised, or mixed: happy:0.6,sad:0.4")
    emo_alpha: float = Field(0.6, ge=0.0, le=1.0)
    max_tokens: int = Field(1500, ge=500, le=3000)
    speed: float = Field(1.0, ge=0.5, le=2.0)
    temperature: float = Field(0.8, ge=0.1, le=2.0)
    top_p: float = Field(0.8, ge=0.0, le=1.0)
    reference_audio: Optional[str] = Field(None, description="Base64-encoded reference audio (WAV)")


class TTSResponse(BaseModel):
    audio_base64: str
    duration_ms: int
    sample_rate: int = 22050
    status: str


class NpzRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded WAV audio to extract speaker from")


# === HELPERS ===
def parse_emotion(emotion_str):
    s = str(emotion_str).strip()
    if ":" in s:
        parts = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                name, weight = part.split(":", 1)
                parts.append(f"{name.split(' ')[0].strip()}:{weight.strip()}")
            else:
                parts.append(part.split(" ")[0].strip())
        return ",".join(parts)
    return s.split(" ")[0].strip()


# === ROUTES ===
@app.post("/api/v1/extract-speaker")
async def extract_speaker(req: NpzRequest):
    """
    Extract speaker embedding (.npz) from generated WAV audio.
    Used for saving a curated voice after iterating through generations.
    Loads model on-demand, runs save_speaker(), releases model.
    """
    try:
        t_start = time.time()
        raw = base64.b64decode(req.audio_base64)

        # Write temp WAV
        wav_path = os.path.join(OUTPUT_DIR, f"_spk_{int(t_start*1000)}.wav")
        with open(wav_path, "wb") as f:
            f.write(raw)
        logger.info(f"WAV saved: {wav_path} ({len(raw)} bytes)")

        # Load model
        model = IndexTTSv2(MODEL_PATH)

        # Extract speaker
        npz_path = os.path.join(OUTPUT_DIR, f"_spk_{int(t_start*1000)}.npz")
        model.save_speaker(wav_path, npz_path)

        # Read NPZ as base64
        with open(npz_path, "rb") as f:
            npz_bytes = f.read()

        # Cleanup
        del model
        gc.collect()
        os.unlink(wav_path)
        os.unlink(npz_path)

        elapsed = time.time() - t_start
        logger.info(f"Speaker extracted in {elapsed:.1f}s, NPZ size={len(npz_bytes)} bytes")

        return {
            "npz_base64": base64.b64encode(npz_bytes).decode("utf-8"),
            "size_bytes": len(npz_bytes),
            "elapsed_s": round(elapsed, 1),
            "status": "ok",
        }

    except Exception as e:
        logger.error(f"Speaker extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0", "model": "IndexTTS2 (MLX 8bit)"}


@app.post("/api/v1/generate", response_model=TTSResponse)
async def generate_tts(req: TTSRequest):
    """Generate speech. Model loaded on-demand, released after."""
    try:
        emotion = parse_emotion(req.emotion)
        logger.info(f"Generate: text={req.text[:50]}... emotion={emotion} α={req.emo_alpha} ref={'custom' if req.reference_audio else 'default'}")

        t_start = time.time()
        model = IndexTTSv2(MODEL_PATH)

        # Determine reference audio path
        if req.reference_audio:
            ref_path = os.path.join(OUTPUT_DIR, f"_ref_{int(t_start*1000)}.wav")
            raw = base64.b64decode(req.reference_audio)
            with open(ref_path, "wb") as f:
                f.write(raw)
            logger.info(f"Using custom reference: {ref_path} ({len(raw)} bytes)")
        else:
            ref_path = DEFAULT_REF

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=OUTPUT_DIR) as tmp:
            output_path = tmp.name

        model.generate(
            text=req.text,
            reference_audio=ref_path,
            output_path=output_path,
            emotion=emotion,
            emo_alpha=req.emo_alpha,
            max_mel_tokens=req.max_tokens,
            speed=req.speed,
            temperature=req.temperature,
            top_p=req.top_p,
        )

        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        duration_ms = int((len(audio_bytes) / (22050 * 2)) * 1000)

        # Release model
        del model
        gc.collect()

        elapsed = time.time() - t_start
        logger.info(f"Done in {elapsed:.1f}s, {duration_ms}ms audio")

        return TTSResponse(
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            duration_ms=duration_ms,
            status="ok"
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === STATIC FILES (mounted last — lowest priority) ===
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

# === MAIN ===
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 IndexTTS2 FastAPI Server")
    print(f"   Model: {MODEL_PATH}")
    print(f"   Default Ref: {DEFAULT_REF}")
    print(f"   Port: {PORT}")
    print(f"   Web UI: http://localhost:{PORT}/")
    print(f"   API: POST http://localhost:{PORT}/api/v1/generate")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")