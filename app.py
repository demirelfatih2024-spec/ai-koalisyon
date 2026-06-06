import streamlit as st
import asyncio
from agents import AGENTS, get_agent_response, get_clients

st.set_page_config(page_title="AI Koalisyonu", page_icon="🤖", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0f1117; color: #e8e8e8; }
.stApp { background-color: #0f1117; }

.app-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase;
    background: #1a2332; color: #4fc3f7;
    border: 1px solid #1e3a5f; border-radius: 6px; padding: 4px 10px; margin-bottom: 12px;
}
.app-title { font-size: 26px; font-weight: 600; color: #ffffff; margin-bottom: 6px; }
.app-sub { font-size: 13px; color: #888; margin-bottom: 1.5rem; }

.agents-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-bottom: 1.5rem; }
.agent-pill { border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 3px; border: 1px solid transparent; }
.pill-purple { background: #150f1f; border-color: #3a1f5f; }
.pill-red    { background: #1f1215; border-color: #4a1b1b; }
.pill-blue   { background: #0d1a2e; border-color: #1e3a5f; }
.pill-green  { background: #0d1f12; border-color: #1a4020; }
.pill-amber  { background: #1f1708; border-color: #4a3800; }
.pill-top { display: flex; align-items: center; justify-content: space-between; }
.pill-name { font-size: 11px; font-weight: 500; }
.pill-role { font-size: 10px; margin-top: 1px; }
.pill-model { font-size: 9px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.5px; margin-top: 2px; }
.pn-purple { color: #ce93d8; } .pr-purple { color: #9c27b0; } .pm-purple { color: #4a1f6a; }
.pn-red { color: #ef9a9a; } .pr-red { color: #c44; } .pm-red { color: #7a3030; }
.pn-blue { color: #90caf9; } .pr-blue { color: #378ADD; } .pm-blue { color: #1e4a80; }
.pn-green { color: #a5d6a7; } .pr-green { color: #4caf50; } .pm-green { color: #1a5c20; }
.pn-amber { color: #ffe082; } .pr-amber { color: #ffa000; } .pm-amber { color: #5c4000; }
.dot { width: 6px; height: 6px; border-radius: 50%; }
.dot-purple { background: #9c27b0; } .dot-red { background: #c44; }
.dot-blue { background: #378ADD; } .dot-green { background: #4caf50; } .dot-amber { background: #ffa000; }

.stTextArea textarea {
    background-color: #161b27 !important; color: #e8e8e8 !important;
    border: 1px solid #2a3a50 !important; border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important; font-size: 14px !important;
}
.stButton > button {
    background: #378ADD !important; color: #fff !important;
    font-family: 'Inter', sans-serif !important; font-weight: 500 !important;
    border: none !important; border-radius: 8px !important;
    padding: 10px 24px !important; width: 100% !important;
}

.debate-q {
    font-size: 12px; font-family: 'JetBrains Mono', monospace;
    color: #4fc3f7; background: #0d1a2e; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 10px 14px; margin-bottom: 1rem;
}

.agent-card { border-radius: 10px; overflow: hidden; margin-bottom: 10px; border: 1px solid transparent; }
.card-purple { background: #120a1f; border-color: #2a1050; }
.card-red    { background: #1a0f0f; border-color: #3a1515; }
.card-blue   { background: #0a1525; border-color: #1a3055; }
.card-green  { background: #0a1a0d; border-color: #153520; }
.card-amber  { background: #1a1205; border-color: #3a2800; }

.card-bar { height: 2px; width: 100%; }
.bar-purple { background: #9c27b0; } .bar-red { background: #c44; }
.bar-blue { background: #378ADD; } .bar-green { background: #4caf50; } .bar-amber { background: #ffa000; }

.card-body { padding: 14px 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.card-meta { display: flex; align-items: center; gap: 8px; }
.card-name { font-size: 13px; font-weight: 500; }
.card-badge { font-size: 10px; border-radius: 5px; padding: 2px 8px; border: 1px solid transparent; }
.badge-purple { background: #1f0f35; color: #ce93d8; border-color: #4a1f70; }
.badge-red    { background: #2a1010; color: #ef9a9a; border-color: #5a2020; }
.badge-blue   { background: #0d2040; color: #90caf9; border-color: #1e4080; }
.badge-green  { background: #0d2510; color: #a5d6a7; border-color: #1a5025; }
.badge-amber  { background: #251800; color: #ffe082; border-color: #503000; }
.card-model { font-size: 10px; font-family: 'JetBrains Mono', monospace; }
.cm-purple { color: #4a1f6a; } .cm-red { color: #7a3030; } .cm-blue { color: #1e4a80; }
.cm-green { color: #1a5c20; } .cm-amber { color: #5c4000; }
.card-text { font-size: 13px; line-height: 1.75; }
.ct-purple { color: #c0a0d0; } .ct-red { color: #d4a0a0; } .ct-blue { color: #9ab8d8; }
.ct-green { color: #90c090; } .ct-amber { color: #d4b870; }

.first-badge {
    font-size: 10px; color: #9c27b0; background: #1f0f35;
    border: 1px solid #4a1f70; border-radius: 4px; padding: 2px 6px; margin-left: 6px;
}
.divider { border: none; border-top: 1px solid #1e2535; margin: 1.5rem 0; }
.status-bar { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #555; margin-top: 1rem; }
.sdot { width: 5px; height: 5px; border-radius: 50%; background: #4caf50; }
</style>
""", unsafe_allow_html=True)

COLOR_CONFIG = {
    "purple": {"pill":"pill-purple","pn":"pn-purple","pr":"pr-purple","pm":"pm-purple","dot":"dot-purple","card":"card-purple","bar":"bar-purple","badge":"badge-purple","cm":"cm-purple","ct":"ct-purple"},
    "red":    {"pill":"pill-red",   "pn":"pn-red",   "pr":"pr-red",   "pm":"pm-red",   "dot":"dot-red",   "card":"card-red",   "bar":"bar-red",   "badge":"badge-red",   "cm":"cm-red",   "ct":"ct-red"},
    "blue":   {"pill":"pill-blue",  "pn":"pn-blue",  "pr":"pr-blue",  "pm":"pm-blue",  "dot":"dot-blue",  "card":"card-blue",  "bar":"bar-blue",  "badge":"badge-blue",  "cm":"cm-blue",  "ct":"ct-blue"},
    "green":  {"pill":"pill-green", "pn":"pn-green", "pr":"pr-green", "pm":"pm-green", "dot":"dot-green", "card":"card-green", "bar":"bar-green", "badge":"badge-green", "cm":"cm-green", "ct":"ct-green"},
    "amber":  {"pill":"pill-amber", "pn":"pn-amber", "pr":"pr-amber", "pm":"pm-amber", "dot":"dot-amber", "card":"card-amber", "bar":"bar-amber", "badge":"badge-amber", "cm":"cm-amber", "ct":"ct-amber"},
}

try:
    ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
    GROQ_KEY      = st.secrets["GROQ_API_KEY"]
except KeyError as e:
    st.error(f"❌ Secrets eksik: {e}")
    st.stop()

claude_client, groq_key = get_clients(ANTHROPIC_KEY, GROQ_KEY)

st.markdown('<div class="app-badge">⚡ AI Coalition System</div>', unsafe_allow_html=True)
st.markdown('<div class="app-title">Koalisyon Danışma Paneli</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">5 uzman ajan sorunuzu analiz eder — planlama uzmanı çerçeveyi çizer, diğerleri kendi alanından katkı sunar.</div>', unsafe_allow_html=True)

grid_html = '<div class="agents-grid">'
for name, cfg in AGENTS.items():
    c = COLOR_CONFIG[cfg["color"]]
    first = ' <span class="first-badge">önce</span>' if name == "Groq-0" else ""
    grid_html += f"""
    <div class="agent-pill {c['pill']}">
        <div class="pill-top">
            <span class="pill-name {c['pn']}">{cfg['emoji']}{first}</span>
            <span class="dot {c['dot']}"></span>
        </div>
        <span class="pill-role {c['pr']}">{cfg['role']}</span>
        <span class="pill-model {c['pm']}">{cfg['model_type']}</span>
    </div>"""
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

question = st.text_area("", placeholder="Örnek: E-ticaret işi kurmayı düşünüyorum, ne dersiniz?", height=100)

if st.button("⚡ Analizi Başlat"):
    if not question.strip():
        st.warning("Lütfen bir soru girin.")
    else:
        st.markdown(f'<div class="debate-q">❓ {question}</div>', unsafe_allow_html=True)
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        previous_text = ""
        for name, config in AGENTS.items():
            c = COLOR_CONFIG[config["color"]]
            with st.spinner(f"{config['emoji']} {config['role']} değerlendiriyor..."):
                response = asyncio.run(
                    get_agent_response(claude_client, groq_key, name, config, question, previous_text)
                )
            previous_text += f"\n{config['role']}: {response}\n"
            st.markdown(f"""
            <div class="agent-card {c['card']}">
                <div class="card-bar {c['bar']}"></div>
                <div class="card-body">
                    <div class="card-header">
                        <div class="card-meta">
                            <span class="dot {c['dot']}"></span>
                            <span class="card-name {c['pn']}">{name}</span>
                            <span class="card-badge {c['badge']}">{config['role']}</span>
                        </div>
                        <span class="card-model {c['cm']}">{config['model_type'].upper()}</span>
                    </div>
                    <p class="card-text {c['ct']}">{response.replace(chr(10), '<br>')}</p>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="status-bar"><span class="sdot"></span>Analiz tamamlandı · 5 uzman · kendi alanından katkı sundu</div>', unsafe_allow_html=True)
