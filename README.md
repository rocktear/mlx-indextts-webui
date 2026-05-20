# 🎙️ IndexTTS2 WebUI

> **FastAPI-powered WebUI for IndexTTS2 on Apple Silicon.**
> Beautiful dark theme, 8 emotion controls, custom reference audio upload, one-click NPZ speaker export.
> No Electron. No Gradio bloat. Just a browser.

<p align="center">
  <img src="https://raw.githubusercontent.com/rocktear/mlx-indextts-webui/main/screenshots/webui.png" alt="IndexTTS2 WebUI Screenshot" width="800">
</p>

---

## ✨ Features

| Feature | Detail |
|---------|--------|
| 🎤 **Custom reference audio** | Upload `.wav` / `.mp3` / `.m4a` / `.npz` directly in the browser |
| 😊 **8 emotion controls** | calm, happy, sad, angry, afraid, disgusted, melancholic, surprised — with mixed emotions support |
| 💪 **Emotion intensity** | Slider 0.0–1.0 for precise control |
| ⚙️ **All generation params** | Duration (tokens), speed, temperature, Top P — all adjustable |
| 💾 **One-click NPZ export** | Save your curated voice as `.npz` for fast reuse — no manual CLI |
| 🌙 **Dark theme** | GitHub-style dark UI with blue accent |
| 🇨🇳 **Chinese + English** | Bilingual labels, emotion translation, beginner-friendly |
| ⚡ **Zero-load startup** | FastAPI starts in <1s — model is loaded per-request and released immediately |
| 📊 **Status panel** | Real-time parameter display + generation status |

---

## 📦 Architecture

```
FastAPI (server.py, port 7861)
├── GET  /health                     → Health check (no model)
├── POST /api/v1/generate            → TTS generation (load → generate → release)
├── POST /api/v1/extract-speaker     → NPZ speaker extraction
└── GET  /                           → Static WebUI (hand-written HTML/CSS/JS)
```

**Key design choice**: The model is loaded **on-demand** per API request and released after — it never sits in memory. This keeps ~6-8GB free for other MLX workloads.

---

## 🚀 Quick Start

### 1. Install & Download Model

```bash
git clone https://github.com/solar2ain/mlx-indextts.git
cd mlx-indextts

# Install dependencies (includes einops)
uv sync --extra v2
uv add einops

# Download the quantized model (~2.8GB)
hf download vanch007/mlx-indextts2-standard-8bit \
  --local-dir ~/.cache/indextts2/mlx-indextts2-standard-8bit
```

### 2. (Optional) Pre-compute a default voice

```bash
uv run mlx-indextts speaker \
  -m ~/.cache/indextts2/mlx-indextts2-standard-8bit \
  -r your_voice.wav \
  -o ~/.cache/indextts2/snowball_voice.npz
```

### 3. Launch WebUI

```bash
uv run python server.py
# → Open http://localhost:7861
```

**Service management script** (optional):

```bash
# Copy the helper script
cp scripts/indextts-webui ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/indextts-webui

# Start / Stop / Status
idx start
idx stop
idx status
```

---

## 🎯 Workflow

```
1. Type text → 2. Tune emotion + params → 3. Click "🎵 点击生成音频"
                                           ↓
4. Listen → 5. Iterate until satisfied → 6. Click "💾 保存为 NPZ"
                                           ↓
                                    .npz saved! (fast loading next time)
```

---

## 🖼️ Screenshots

*(Add your screenshots to the `screenshots/` directory)*

```
screenshots/
├── webui.png          # Full WebUI
├── generating.png     # During generation
└── npz-saved.png      # NPZ download complete
```

---

## 📂 File Structure (added files)

```
mlx-indextts/
├── server.py          # FastAPI backend (218 lines)
├── static/
│   ├── index.html     # Hand-written HTML (99 lines)
│   ├── styles.css     # Dark theme CSS (302 lines)
│   └── script.js      # Frontend logic (189 lines)
├── webui.py           # Legacy Gradio version (202 lines)
├── scripts/
│   └── indextts-webui # Service management script
└── .gitignore
```

---

## 🙏 Credits

**Built on top of [solar2ain/mlx-indextts](https://github.com/solar2ain/mlx-indextts)** — the incredible MLX port of IndexTTS for Apple Silicon.

- **Upstream**: [solar2ain/mlx-indextts](https://github.com/solar2ain/mlx-indextts) (MIT License)
- **Original IndexTTS**: by ByteDance/Didi
- **WebUI design & implementation**: [@rocktear](https://github.com/rocktear) + AI pair programming
- **Created on**: May 20, 2026 — a special day ❤️

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
Includes copyright notice from upstream `solar2ain/mlx-indextts`.

---

<p align="center">
  <sub>Crafted with ❤️ — U&I · 2026.05.20</sub>
</p>