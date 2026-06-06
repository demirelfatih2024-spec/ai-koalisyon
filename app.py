import streamlit as st
import asyncio
from agents import AGENTS, get_agent_response, get_clients

st.set_page_config(
    page_title="AI Koalisyonu",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; background-color: #0d0d0d; color: #e8e8e8; }
.stApp { background-color: #0d0d0d; }
.agent-card { background: #161616; border: 1px solid #2a2a2a; border-radius: 12px; padding: 20px 24px; margin: 16px 0; }
.agent-header { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
.agent-body { font-size: 0.95rem; line-height: 1.7; color: #cccccc; }
.color-blue  { border-left: 3px solid #4fc3f7; padding-left: 16px; }
.color-green { border-left: 3px solid #81c784; padding-left: 16px; }
.color-yellow{ border-left: 3px solid #ffd54f; padding-left: 16px; }
.color-red   { border-left: 3px solid #ef9a9a; padding-left: 16px; }
.divider { border: none; border-top: 1px solid #222; margin: 24px 0; }
.stTextArea textarea { background-color: #161616 !important; color: #e8e8e8 !important; border: 1px solid #2a2a2a !important; border-radius: 10px !important; font-size: 1rem !important; }
.stButton > button { background: #ffffff !important; color: #0d0d0d !important; font-weight: 700 !important; border: none !important; border-radius: 8px !important; padding: 10px 28px !important; width: 100% !important; }
</style>
""", unsafe_allow_html=True)

COLOR_MAP = {"🔵": "color-blue", "🟢": "color-green", "🟡": "color-yellow", "🔴": "color-red"}

try:
    ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
    GROQ_KEY      = st.secrets["GROQ_API_KEY"]
except KeyError as e:
    st.error(f"❌ Secrets eksik: {e} — Streamlit Cloud'da Settings > Secrets bölümüne anahtarları ekle.")
    st.stop()

claude_client, groq_key = get_clients(ANTHROPIC_KEY, GROQ_KEY)

st.markdown("## 🤖 AI Koalisyonu")
st.markdown("Sorunuzu yazın — 4 ajan farklı perspektiflerden tartışsın.")
st.markdown("<hr class='divider'>", unsafe_allow_html=True)

with st.expander("👥 Aktif Ajanlar"):
    for name, cfg in AGENTS.items():
        st.markdown(f"**{cfg['emoji']} {name}** — `{cfg['model_type'].upper()}`")

question = st.text_area("Sorunuz:", placeholder="Örnek: Yapay zeka insanların işini elinden alacak mı?", height=100, label_visibility="collapsed")

if st.button("⚡ Tartışmayı Başlat"):
    if not question.strip():
        st.warning("Lütfen bir soru girin.")
    else:
        st.markdown(f"<div style='background:#161616;border:1px solid #333;border-radius:10px;padding:14px 18px;font-family:monospace;font-size:0.85rem;color:#aaa;margin-bottom:24px'>❓ {question}</div>", unsafe_allow_html=True)

        previous_text = ""

        for name, config in AGENTS.items():
            emoji = config["emoji"]
            color_class = COLOR_MAP.get(emoji, "")

            with st.spinner(f"{emoji} {name} düşünüyor..."):
                response = asyncio.run(
                    get_agent_response(claude_client, groq_key, name, config, question, previous_text)
                )

            previous_text += f"\n{name}: {response}\n"

            st.markdown(f"""
            <div class="agent-card {color_class}">
                <div class="agent-header">{emoji} {name} · {config['model_type'].upper()}</div>
                <div class="agent-body">{response.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)
        st.success("✅ Tartışma tamamlandı.")
