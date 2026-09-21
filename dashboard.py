"""
AI Video Pipeline Dashboard
Запуск: streamlit run dashboard.py
"""
import os
import sys
import glob
import html
import subprocess
import time
import random
import streamlit as st
from pathlib import Path

# ─── Пути ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
OUTPUTS_DIR  = ROOT / "outputs"
TEMP_DIR     = ROOT / "temp_assets"
MUSIC_DIR    = ROOT / "music"
ENV_FILE     = ROOT / ".env"

OUTPUTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(exist_ok=True)

# ─── Загрузка .env ─────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def save_env(data: dict):
    lines = [f"{k}={v}" for k, v in data.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Dark background */
    .stApp { background: #0d0f14; color: #e8eaf0; }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1a1d2e 0%, #12151f 100%);
        border: 1px solid #2a2d3e;
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .main-header h1 { margin: 0; font-size: 28px; font-weight: 700; color: #fff; }
    .main-header p { margin: 4px 0 0; color: #6b7280; font-size: 14px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #12151f;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid #1e2130;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #6b7280;
        font-weight: 500;
        padding: 8px 20px;
        transition: all 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background: #1e3a5f !important;
        color: #60a5fa !important;
    }

    /* Cards */
    .card {
        background: #12151f;
        border: 1px solid #1e2130;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .card h3 { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background: #1a1d2e !important;
        border: 1px solid #2a2d3e !important;
        border-radius: 10px !important;
        color: #e8eaf0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }

    /* Sliders */
    .stSlider [data-baseweb="slider"] { padding: 0; }

    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        padding: 14px;
        border: none;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
    }

    /* Log area */
    .log-box {
        background: #090b10;
        border: 1px solid #1e2130;
        border-radius: 10px;
        padding: 16px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 12px;
        line-height: 1.7;
        max-height: 380px;
        overflow-y: auto;
        color: #a8b4c8;
        white-space: pre-wrap;
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; }
    .badge-green { background: rgba(34,197,94,0.15); color: #4ade80; }
    .badge-yellow { background: rgba(234,179,8,0.15); color: #facc15; }

    /* Video card */
    .video-item {
        background: #12151f;
        border: 1px solid #1e2130;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .video-name { font-size: 13px; font-weight: 600; color: #9ca3af; margin-bottom: 8px; }

    /* Metric boxes */
    .metric-box {
        background: #12151f;
        border: 1px solid #1e2130;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #60a5fa; }
    .metric-label { font-size: 12px; color: #6b7280; margin-top: 4px; }

    /* Hide Streamlit default elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .block-container { padding-top: 20px !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <div style="font-size:40px">🎬</div>
    <div>
        <h1>AI Video Studio</h1>
        <p>Keyword → Script → Images → Video → Reels. Fully automated.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab_gen, tab_gallery, tab_settings = st.tabs(["🚀 Generate", "🗂️ Gallery", "⚙️ Settings"])


# ══════════════════════════════════════════════════════════════════
#  TAB 1 — GENERATE
# ══════════════════════════════════════════════════════════════════
with tab_gen:
    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.markdown('<div class="card"><h3>🔑 Keywords</h3>', unsafe_allow_html=True)
        keywords = st.text_area(
            "Keywords",
            placeholder="ocean, storm, survival\nAI future loneliness\ntokyo neon rain cyberpunk",
            height=110,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><h3>⚙️ Generation Settings</h3>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            scene_count = st.slider("Сцен в видео", 1, 6, 2)
        with c2:
            music_volume = st.slider("Громкость музыки", 0, 40, 12, format="%d%%")

        # Список треков в music/
        music_tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
        if music_tracks:
            track_names = [t.name for t in music_tracks]
            selected_track = st.selectbox(
                "🎵 Фоновый трек",
                ["🎲 Случайный"] + track_names,
            )
        else:
            st.info("📂 Папка `music/` пуста. Добавь MP3-треки для фоновой музыки.")
            selected_track = None
        st.markdown("</div>", unsafe_allow_html=True)

        # Кнопка запуска — всегда активна, валидация внутри
        run_btn = st.button("▶ Запустить генерацию", type="primary")

    with col_right:
        st.markdown('<div class="card"><h3>📊 Статус</h3>', unsafe_allow_html=True)

        # Метрики
        videos = list(OUTPUTS_DIR.glob("*.mp4"))
        music_count = len(music_tracks) if music_tracks else 0

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{len(videos)}</div><div class="metric-label">Видео готово</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{music_count}</div><div class="metric-label">Треков в папке</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-box"><div class="metric-value">{scene_count}</div><div class="metric-label">Сцен</div></div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Лог-панель
        st.markdown('<div class="card"><h3>📋 Live Log</h3>', unsafe_allow_html=True)
        log_placeholder = st.empty()
        log_placeholder.markdown('<div class="log-box">Жди старта генерации...</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Превью последнего видео
        video_placeholder = st.empty()

    # ── Запуск генерации ──────────────────────────────────────────
    if run_btn:
        if not keywords.strip():
            st.warning("⚠️ Введи ключевые слова перед запуском!")
            st.stop()
        # Временно переопределяем переменные окружения
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"          # ← отключает буферизацию stdout
        env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
        env["SCENE_COUNT_MIN"] = str(scene_count)
        env["SCENE_COUNT_MAX"] = str(scene_count)
        env["BG_MUSIC_VOLUME"] = str(music_volume / 100)

        # Определяем трек
        if selected_track and selected_track != "🎲 Случайный" and music_tracks:
            env["BG_MUSIC_DIR"] = str(MUSIC_DIR)
        else:
            env["BG_MUSIC_DIR"] = str(MUSIC_DIR)

        # Генерируем имя выходного файла
        safe_kw = "_".join(keywords.strip().split(",")[0].strip().split()[:3])
        timestamp = int(time.time())
        output_name = f"reel_{safe_kw}_{timestamp}.mp4"

        # Создаём runner-скрипт чтобы передать keywords без stdin
        runner_path = ROOT / "_runner.py"
        runner_path.write_text(f"""
import os, sys
sys.path.insert(0, r"{ROOT}")
os.environ["SCENE_COUNT_MIN"] = "{scene_count}"
os.environ["SCENE_COUNT_MAX"] = "{scene_count}"
os.environ["BG_MUSIC_VOLUME"] = "{music_volume / 100}"
os.environ["BG_MUSIC_DIR"] = r"{MUSIC_DIR}"

from config import TEMP_DIR, OUTPUT_DIR, BG_MUSIC_DIR, BG_MUSIC_VOLUME
from llm import generate_storyboard
from generation import generate_image_flux, generate_video_ltx2, download_file
from audio import generate_voiceover
from assembly import assemble_final_video
from antidetect import apply_antidetect_measures
import os as _os

_os.makedirs(TEMP_DIR, exist_ok=True)
_os.makedirs(OUTPUT_DIR, exist_ok=True)

# Очищаем temp
for f in _os.listdir(TEMP_DIR):
    try: _os.remove(_os.path.join(TEMP_DIR, f))
    except: pass

keywords = {repr(keywords.strip())}
storyboard = generate_storyboard(keywords)

scenes_data = storyboard.get("scenes", [])
global_style = storyboard.get("video_metadata", {{}}).get("global_style", "")

scene_files = []
for idx, scene in enumerate(scenes_data):
    full_prompt = f"{{scene['image_prompt']}}, {{global_style}}"
    global_neg = storyboard.get("video_metadata", {{}}).get("global_negative_prompt", "")
    scene_neg = scene.get("negative_prompt", "")
    negative_prompt = ", ".join(filter(None, [global_neg, scene_neg]))
    img_url = generate_image_flux(full_prompt, negative_prompt)
    video_url = generate_video_ltx2(img_url, scene['ltx2_motion'])
    video_file = _os.path.join(TEMP_DIR, f"scene_{{idx:02d}}.mp4")
    download_file(video_url, video_file)
    audio_prefix = _os.path.join(TEMP_DIR, f"audio_{{idx:02d}}")
    audio_file, word_timings = generate_voiceover(scene['voiceover_text'], audio_prefix)
    scene_files.append({{"video": video_file, "audio": audio_file, "word_timings": word_timings}})

montage_output = _os.path.join(OUTPUT_DIR, "raw_montage.mp4")
assemble_final_video(scene_files, [], montage_output, crossfade_duration=0.5,
                     bg_music_path=BG_MUSIC_DIR, bg_music_volume=BG_MUSIC_VOLUME)

safe_output = _os.path.join(OUTPUT_DIR, "{output_name}")
apply_antidetect_measures(montage_output, safe_output)
print(f"DONE:{{safe_output}}")
""", encoding="utf-8")

        log_lines = []
        final_video_path = None

        proc = subprocess.Popen(
            [sys.executable, "-u", str(runner_path)],  # -u = unbuffered stdout
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=env,
        )

        for line in proc.stdout:
            line = line.rstrip()
            if line.startswith("DONE:"):
                final_video_path = line[5:].strip()
                log_lines.append("✅ ГОТОВО!")
            else:
                log_lines.append(line)

            log_html = "\n".join(html.escape(l) for l in log_lines[-60:])
            log_placeholder.markdown(f'<div class="log-box">{log_html}</div>', unsafe_allow_html=True)

        proc.wait()
        runner_path.unlink(missing_ok=True)

        if final_video_path and Path(final_video_path).exists():
            video_placeholder.video(str(final_video_path))
            st.success(f"🎉 Видео готово: `{Path(final_video_path).name}`")
        elif proc.returncode != 0:
            st.error("❌ Ошибка генерации. Смотри лог выше.")


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — GALLERY
# ══════════════════════════════════════════════════════════════════
with tab_gallery:
    videos = sorted(OUTPUTS_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True)

    if not videos:
        st.markdown("""
        <div style="text-align:center; padding:60px; color:#4b5563;">
            <div style="font-size:48px; margin-bottom:16px">🎬</div>
            <div style="font-size:18px; font-weight:600;">Нет готовых видео</div>
            <div style="font-size:14px; margin-top:8px;">Запусти генерацию на вкладке Generate</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(videos)} видео** в `outputs/`")
        cols = st.columns(2)
        for i, vp in enumerate(videos):
            with cols[i % 2]:
                size_mb = vp.stat().st_size / 1_048_576
                mtime = time.strftime("%d.%m.%Y %H:%M", time.localtime(vp.stat().st_mtime))
                st.markdown(f'<div class="video-name">📹 {vp.name} &nbsp;<span class="badge badge-blue">{size_mb:.1f} MB</span>&nbsp;<span class="badge badge-yellow">{mtime}</span></div>', unsafe_allow_html=True)
                st.video(str(vp))
                with open(vp, "rb") as f:
                    st.download_button(
                        "⬇ Скачать",
                        data=f,
                        file_name=vp.name,
                        mime="video/mp4",
                        key=f"dl_{vp.name}",
                    )


# ══════════════════════════════════════════════════════════════════
#  TAB 3 — SETTINGS
# ══════════════════════════════════════════════════════════════════
with tab_settings:
    env_data = load_env()

    col_s1, col_s2 = st.columns(2, gap="large")

    with col_s1:
        st.markdown('<div class="card"><h3>🔐 API Keys</h3>', unsafe_allow_html=True)
        openrouter_key = st.text_input(
            "OpenRouter API Key",
            value=env_data.get("OPENROUTER_API_KEY", ""),
            type="password",
            placeholder="sk-or-v1-...",
        )
        runpod_key = st.text_input(
            "RunPod API Key",
            value=env_data.get("RUNPOD_API_KEY", ""),
            type="password",
            placeholder="rpa_...",
        )
        ltx2_endpoint = st.text_input(
            "LTX2 Endpoint ID",
            value=env_data.get("LTX2_ENDPOINT", ""),
            placeholder="xn89jra96sz8y1",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><h3>🗄️ RunPod S3</h3>', unsafe_allow_html=True)
        s3_access = st.text_input("S3 Access Key", value=env_data.get("RUNPOD_S3_ACCESS_KEY", ""), type="password")
        s3_secret = st.text_input("S3 Secret Key", value=env_data.get("RUNPOD_S3_SECRET_KEY", ""), type="password")
        s3_bucket = st.text_input("S3 Bucket Name", value=env_data.get("RUNPOD_S3_BUCKET", ""))
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("💾 Сохранить настройки", type="primary"):
            new_env = {
                "OPENROUTER_API_KEY": openrouter_key,
                "RUNPOD_API_KEY": runpod_key,
                "LTX2_ENDPOINT": ltx2_endpoint,
                "RUNPOD_S3_ACCESS_KEY": s3_access,
                "RUNPOD_S3_SECRET_KEY": s3_secret,
                "RUNPOD_S3_BUCKET": s3_bucket,
            }
            save_env({k: v for k, v in new_env.items() if v})
            st.success("✅ Настройки сохранены в `.env`")

    with col_s2:
        st.markdown('<div class="card"><h3>🎵 Треки в папке music/</h3>', unsafe_allow_html=True)
        all_tracks = sorted(MUSIC_DIR.glob("*.mp3")) + sorted(MUSIC_DIR.glob("*.wav"))
        if all_tracks:
            for t in all_tracks:
                size_kb = t.stat().st_size // 1024
                tc1, tc2 = st.columns([4, 1])
                with tc1:
                    st.markdown(f"🎵 `{t.name}` &nbsp;<span class='badge badge-blue'>{size_kb} KB</span>", unsafe_allow_html=True)
                with tc2:
                    if st.button("🗑", key=f"del_{t.name}", help="Удалить трек"):
                        t.unlink()
                        st.rerun()
        else:
            st.markdown("""
            <div style="text-align:center; padding:30px; color:#4b5563;">
                <div style="font-size:32px">🎵</div>
                <div>Папка <code>music/</code> пуста</div>
                <div style="font-size:12px; margin-top:8px;">Скачай треки на <b>pixabay.com/music</b> и положи сюда</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><h3>📁 Пути к папкам</h3>', unsafe_allow_html=True)
        st.code(f"""outputs/     → {OUTPUTS_DIR}
temp_assets/ → {TEMP_DIR}
music/       → {MUSIC_DIR}
.env         → {ENV_FILE}""", language="bash")
        st.markdown("</div>", unsafe_allow_html=True)
