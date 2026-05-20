// IndexTTS2 声音克隆 — 前端逻辑
const API = '/api/v1/generate';

// DOM refs
const $ = (sel) => document.querySelector(sel);
const textInput = $('#text-input');
const emotionSelect = $('#emotion-select');
const emotionCustom = $('#emotion-custom');
const emoAlpha = $('#emo-alpha');
const maxTokens = $('#max-tokens');
const speed = $('#speed');
const temperature = $('#temperature');
const topP = $('#top-p');
const audioPlayer = $('#audio-player');
const progressBar = $('#progress-bar');
const progressFill = $('#progress-fill');
const progressText = $('#progress-text');
const generateBtn = $('#generate-btn');
const saveNpzBtn = $('#save-npz-btn');
const saveNpzStatus = $('#save-npz-status');
const statusText = $('#status-text');
const refAudioInput = $('#ref-audio-file');
const refAudioName = $('#ref-audio-name');

// Slider value sync
document.querySelectorAll('input[type="range"]').forEach(slider => {
    const span = $(`#${slider.id}-val`);
    slider.addEventListener('input', () => {
        if (slider.id === 'speed') span.textContent = `${slider.value}x`;
        else span.textContent = slider.value;
    });
});

// Emotion select → toggle custom input
emotionSelect.addEventListener('change', () => {
    if (emotionSelect.value === '__custom__') {
        emotionCustom.classList.remove('hidden');
        emotionCustom.focus();
    } else {
        emotionCustom.classList.add('hidden');
        emotionCustom.value = '';
    }
});

// Examples
const examples = [
    { text: '这是我为你精心准备的声音。', emotion: 'calm 平静', alpha: 0.6, tokens: 1500, speed: 1.0 },
    { text: '今天真是太开心了！一起去庆祝吧！', emotion: 'happy 高兴', alpha: 0.7, tokens: 1500, speed: 1.0 },
    { text: '有时候我会感到有点难过和失落。', emotion: 'sad 伤心', alpha: 0.6, tokens: 1500, speed: 1.0 },
    { text: '你怎么敢这样对我！', emotion: 'angry 愤怒', alpha: 0.8, tokens: 1500, speed: 1.0 },
    { text: '我有点害怕…不知道会发生什么。', emotion: 'afraid 害怕', alpha: 0.6, tokens: 1500, speed: 1.0 },
    { text: '这真是令人厌恶，我无法接受。', emotion: 'disgusted 厌恶', alpha: 0.7, tokens: 1500, speed: 1.0 },
    { text: '一切都显得那么沉闷和无趣。', emotion: 'melancholic 忧郁', alpha: 0.6, tokens: 1500, speed: 1.0 },
    { text: '哇！这真是太惊人了！', emotion: 'surprised 惊讶', alpha: 0.7, tokens: 1500, speed: 1.0 },
    { text: '又开心又紧张，这种感觉很奇妙。', emotion: 'mixed 混合情绪', alpha: 0.6, tokens: 1500, speed: 1.0, custom: 'happy:0.6,surprised:0.4' },
];

const examplesGrid = $('#examples-grid');
examples.forEach(ex => {
    const card = document.createElement('div');
    card.className = 'example-card';
    card.innerHTML = `<div class="emo">${ex.emotion}</div><div class="txt">${ex.text}</div>`;
    card.addEventListener('click', () => {
        textInput.value = ex.text;
        if (ex.custom) {
            emotionSelect.value = '__custom__';
            emotionCustom.classList.remove('hidden');
            emotionCustom.value = ex.custom;
        } else {
            emotionSelect.value = ex.emotion;
            emotionCustom.classList.add('hidden');
            emotionCustom.value = '';
        }
        emoAlpha.value = ex.alpha;
        maxTokens.value = ex.tokens;
        speed.value = ex.speed;
        document.querySelectorAll('input[type="range"]').forEach(s => s.dispatchEvent(new Event('input')));
    });
    examplesGrid.appendChild(card);
});

// State
let refAudioBase64 = null;
let lastWavBase64 = null;  // most recently generated WAV, for NPZ save
refAudioInput.addEventListener('change', () => {
    const f = refAudioInput.files[0];
    if (!f) { refAudioBase64 = null; refAudioName.textContent = ''; return; }
    refAudioName.textContent = `⏳ 读取 ${f.name}…`;
    const reader = new FileReader();
    reader.onload = () => {
        refAudioBase64 = reader.result.split(',')[1];  // strip data:... prefix
        refAudioName.textContent = `✅ ${f.name}`;
    };
    reader.readAsDataURL(f);
});

// Generate
generateBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) { statusText.textContent = '❌ 请输入文本'; return; }

    generateBtn.disabled = true;
    progressBar.classList.remove('hidden');
    progressFill.style.width = '0';
    progressText.textContent = '生成中…';
    statusText.textContent = '⏳ 处理中…';

    // Simulate progress (model doesn't stream)
    let w = 0;
    const progressInterval = setInterval(() => {
        w = Math.min(w + Math.random() * 15, 90);
        progressFill.style.width = `${w}%`;
    }, 1000);

    try {
        const emotionVal = emotionCustom.value.trim() || emotionSelect.value;
        const body = {
            text,
            emotion: emotionVal,
            emo_alpha: parseFloat(emoAlpha.value),
            max_tokens: parseInt(maxTokens.value),
            speed: parseFloat(speed.value),
            temperature: parseFloat(temperature.value),
            top_p: parseFloat(topP.value),
        };
        if (refAudioBase64) body.reference_audio = refAudioBase64;

        const resp = await fetch(API, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = '完成！';

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Unknown error');
        }

        const data = await resp.json();
        audioPlayer.src = `data:audio/wav;base64,${data.audio_base64}`;
        audioPlayer.style.display = 'block';
        lastWavBase64 = data.audio_base64;  // stash for NPZ save
        saveNpzBtn.disabled = false;
        saveNpzBtn.title = '保存为 NPZ 文件';
        saveNpzStatus.textContent = '';

        statusText.textContent = '✅ 生成成功';
        const emoLabel = emotionCustom.value.trim() ? 'mixed' : emotionSelect.value.split(' ')[0];
        $('#param-emotion').textContent = emoLabel;
        $('#param-alpha').textContent = emoAlpha.value;
        $('#param-tokens').textContent = `${maxTokens.value} tokens`;
        $('#param-speed').textContent = `${speed.value}x`;
        $('#param-temp').textContent = temperature.value;
        $('#param-topp').textContent = topP.value;

    } catch (err) {
        clearInterval(progressInterval);
        progressFill.style.width = '0';
        progressText.textContent = '失败';
        statusText.textContent = `❌ ${err.message}`;
    } finally {
        setTimeout(() => {
            progressBar.classList.add('hidden');
            progressFill.style.width = '0';
        }, 2000);
        generateBtn.disabled = false;
    }
});

// Save NPZ
saveNpzBtn.addEventListener('click', async () => {
    if (!lastWavBase64) return;
    saveNpzBtn.disabled = true;
    saveNpzStatus.textContent = '⏳ 提取中…';
    saveNpzStatus.style.color = 'var(--text-dim)';

    try {
        const resp = await fetch('/api/v1/extract-speaker', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: lastWavBase64 }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Unknown error');
        }
        const data = await resp.json();

        // Trigger download
        const blob = new Blob(
            [Uint8Array.from(atob(data.npz_base64), c => c.charCodeAt(0))],
            { type: 'application/octet-stream' }
        );
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `voice_${Date.now()}.npz`;
        a.click();
        URL.revokeObjectURL(url);

        saveNpzStatus.textContent = `✅ 已下载 (${(data.size_bytes/1024).toFixed(0)}KB, ${data.elapsed_s}s)`;
        saveNpzStatus.style.color = 'var(--green)';
    } catch (err) {
        saveNpzStatus.textContent = `❌ ${err.message}`;
        saveNpzStatus.style.color = '#f85149';
    } finally {
        saveNpzBtn.disabled = false;
    }
});