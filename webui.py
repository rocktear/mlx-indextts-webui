"""
IndexTTS2 Gradio WebUI — 最终完美版
四行布局 × 审美统一
参考音 + 生成参数 + 点击生成音频按钮
"""
import os
import sys
import tempfile
import warnings
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import gradio as gr

try:
    from mlx_indextts.generate_v2 import IndexTTSv2
except ImportError:
    print("Error: 'mlx-indextts' library not found.")
    sys.exit(1)

MODEL_PATH = os.path.expanduser("~/.cache/indextts2/mlx-indextts2-standard-8bit")
DEFAULT_REF_AUDIO_PATH = os.path.expanduser("~/.cache/indextts2/snowball_voice.npz")
OUTPUT_DIR = os.path.expanduser("~/mlx-indextts/outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

tts_model = None

EMOTION_CHOICES = [
    "calm 平静", "happy 高兴", "sad 伤心", "angry 愤怒",
    "afraid 害怕", "disgusted 厌恶", "melancholic 忧郁", "surprised 惊讶"
]

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
                name = name.split(" ")[0].strip()
                parts.append(f"{name}:{weight.strip()}")
            else:
                parts.append(part.split(" ")[0].strip())
        return ",".join(parts)
    return s.split(" ")[0].strip()

def load_model():
    global tts_model
    if tts_model is not None:
        return tts_model
    tts_model = IndexTTSv2(MODEL_PATH)
    return tts_model

def generate_speech(text, ref_audio_file, emotion, emo_alpha, max_tokens, speed, temperature, top_p):
    if not text.strip():
        return None, "❌ 请输入文本"
    try:
        parsed_emotion = parse_emotion(emotion)
        ref_audio_path = ref_audio_file if ref_audio_file is not None else DEFAULT_REF_AUDIO_PATH
        model = load_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=OUTPUT_DIR) as tmp:
            output_path = tmp.name
        model.generate(
            text=text, reference_audio=ref_audio_path, output_path=output_path,
            emotion=parsed_emotion, emo_alpha=emo_alpha,
            max_mel_tokens=max_tokens, speed=speed,
            temperature=temperature, top_p=top_p,
        )
        status_msg = (
            f"✅ 情绪：{parsed_emotion}\n"
            f"💪 强度：{emo_alpha}\n"
            f"⏱️ 时长：{max_tokens} tokens\n"
            f"🚀 语速：{speed}x\n"
            f"🎲 Temp：{temperature}\n"
            f"📊 TopP：{top_p}"
        )
        return output_path, status_msg
    except Exception as e:
        return None, f"❌ {str(e)}"

with gr.Blocks(title="IndexTTS2 WebUI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎙️ IndexTTS2 声音克隆")
    
    # ===== 第一行：文本（独占） =====
    with gr.Row():
        gr.Markdown("### 📝 文本")
    with gr.Row():
        text_input = gr.TextArea(
            label="输入文本",
            placeholder="请输入要合成的文本...",
            lines=6, max_lines=10,
            scale=1
        )
    
    # ===== 第二行：情绪控制 + 生成参数 =====
    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### 😊 情绪控制")
            emotion = gr.Dropdown(
                choices=EMOTION_CHOICES, value="calm 平静",
                label="情绪（支持混合）",
                scale=1
            )
            emo_alpha = gr.Slider(
                minimum=0.0, maximum=1.0, value=0.6, step=0.05,
                label="💪 强度", scale=1
            )
        
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### ⚙️ 生成参数")
            with gr.Row():
                max_tokens = gr.Slider(
                    minimum=500, maximum=3000, value=1500, step=100,
                    label="⏱️ 时长", scale=1
                )
                speed = gr.Slider(
                    minimum=0.5, maximum=2.0, value=1.0, step=0.1,
                    label="🚀 语速", scale=1
                )
            with gr.Row():
                temperature = gr.Slider(
                    minimum=0.1, maximum=2.0, value=0.8, step=0.1,
                    label="🎲 Temp", scale=1
                )
                top_p = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.8, step=0.05,
                    label="📊 TopP", scale=1
                )
    
    # ===== 第三行：输出（独占） =====
    with gr.Row():
        gr.Markdown("### 🔊 输出")
    with gr.Row():
        audio_output = gr.Audio(
            label="生成的音频",
            type="filepath",
            interactive=False,
            scale=1
        )
    
    # ===== 第四行：参考音 + 生成参数 + 生成按钮 =====
    with gr.Row():
        # 左 — 参考音（保留完整播放器和剪辑功能）
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### 🎤 输入")
            ref_audio_file = gr.Audio(
                label="参考的音频",
                type="filepath",
                sources=["upload"],
                scale=1
            )
        
        # 右 — 状态 + 生成按钮
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### 📊 状态")
            status_output = gr.Textbox(
                label="数值",
                interactive=False,
                lines=6, max_lines=6,
                placeholder="点击「生成」后，此处将显示所有使用的参数...",
                scale=1
            )
            generate_btn = gr.Button(
                "🎵 点击生成音频",
                variant="primary",
                size="lg",
                scale=1
            )
    
    # 示例
    gr.Examples(
        examples=[
            ["这是我为你精心准备的声音。希望你喜欢这个温柔的嗓音。", None, "calm 平静", 0.6, 1500, 1.0],
            ["今天真是太开心了！我们一起去庆祝吧！", None, "happy 高兴", 0.7, 1500, 1.0],
            ["有时候我会感到有点难过和失落。", None, "sad 伤心", 0.6, 1500, 1.0],
            ["你怎么敢这样对我！我很生气！", None, "angry 愤怒", 0.8, 1500, 1.0],
            ["我有点害怕，不知道会发生什么。", None, "afraid 害怕", 0.6, 1500, 1.0],
            ["这真是令人厌恶，我无法接受。", None, "disgusted 厌恶", 0.7, 1500, 1.0],
            ["一切都显得那么沉闷和无趣。", None, "melancholic 忧郁", 0.6, 1500, 1.0],
            ["哇！这真是太惊人了！", None, "surprised 惊讶", 0.7, 1500, 1.0],
        ],
        inputs=[text_input, ref_audio_file, emotion, emo_alpha, max_tokens, speed],
        label="💡 示例"
    )
    
    generate_btn.click(
        fn=generate_speech,
        inputs=[text_input, ref_audio_file, emotion, emo_alpha, max_tokens, speed, temperature, top_p],
        outputs=[audio_output, status_output],
        show_progress="full"
    )

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 IndexTTS2 Gradio WebUI — 最终完美版")
    print("=" * 60)
    demo.launch(server_name="0.0.0.0", server_port=7861, share=False, show_error=True)