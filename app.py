import streamlit as st
import asyncio
from agents import AGENTS, COORDINATOR, get_agent_response, get_coordinator_response, get_clients

st.set_page_config(page_title="AI Koalisyonu", page_icon="🤖", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0f1117; color: #e8e8e8; }
.stApp { background-color: #0f1117; }

.app-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase; background: #1a2332; color: #4fc3f7; border: 1px solid #1e3a5f; border-radius: 6px; padding: 4px 10px; margin-bottom: 12px; }
.app-title { font-size: 26px; font-weight: 600; color: #ffffff; margin-bottom: 6px; }
.app-sub { font-size: 13px; color: #888; margin-bottom: 1.5rem; }

.agents-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-bottom: 1.5rem; }
.agent-pill { border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 3px; border: 1px solid transparent; }
.pill-purple { background: #150f1f; border-color: #3a1f5f; }
.pill-red    { background: #1f1215; border-color: #4a1b1b; }
.pill-blue   { background: #0d1a2e; border-color: #1e3a5f; }
.pill-green  { background: #0d1f12; border-color: #1a4020; }
.pill-amber  { background: #1f1708; border-color: #4a3800; }
.pill-white  { background: #1a1c22; border-color: #3a3d4a; }
.pill-top { display: flex; align-items: center; justify-content: space-between; }
.pill-name { font-size: 10px; font-weight: 500; }
.pill-role { font-size: 9px; margin-top: 1px; }
.pill-model { font-size: 9px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.5px; margin-top: 2px; }
.pn-purple{color:#ce93d8;} .pr-purple{color:#9c27b0;} .pm-purple{color:#4a1f6a;}
.pn-red{color:#ef9a9a;} .pr-red{color:#c44;} .pm-red{color:#7a3030;}
.pn-blue{color:#90caf9;} .pr-blue{color:#378ADD;} .pm-blue{color:#1e4a80;}
.pn-green{color:#a5d6a7;} .pr-green{color:#4caf50;} .pm-green{color:#1a5c20;}
.pn-amber{color:#ffe082;} .pr-amber{color:#ffa000;} .pm-amber{color:#5c4000;}
.pn-white{color:#ccc;} .pr-white{color:#888;} .pm-white{color:#444;}
.dot{width:6px;height:6px;border-radius:50%;}
.dot-purple{background:#9c27b0;} .dot-red{background:#c44;} .dot-blue{background:#378ADD;}
.dot-green{background:#4caf50;} .dot-amber{background:#ffa000;} .dot-white{background:#666;}

.stTextArea textarea { background-color:#161b27!important; color:#e8e8e8!important; border:1px solid #2a3a50!important; border-radius:10px!important; font-family:'Inter',sans-serif!important; font-size:14px!important; }
.stButton > button { background:#378ADD!important; color:#fff!important; font-family:'Inter',sans-serif!important; font-weight:500!important; border:none!important; border-radius:8px!important; padding:10px 24px!important; width:100%!important; }

.debate-q { font-size:12px; font-family:'JetBrains Mono',monospace; color:#4fc3f7; background:#0d1a2e; border:1px solid #1e3a5f; border-radius:8px; padding:10px 14px; margin-bottom:1rem; }

.agent-card { border-radius:10px; overflow:hidden; margin-bottom:10px; border:1px solid transparent; }
.card-purple{background:#120a1f;border-color:#2a1050;}
.card-red{background:#1a0f0f;border-color:#3a1515;}
.card-blue{background:#0a1525;border-color:#1a3055;}
.card-green{background:#0a1a0d;border-color:#153520;}
.card-amber{background:#1a1205;border-color:#3a2800;}
.card-white{background:#13151c;border-color:#2a2d3a;}

.card-bar{height:2px;width:100%;}
.bar-purple{background:#9c27b0;} .bar-red{background:#c44;} .bar-blue{background:#378ADD;}
.bar-green{background:#4caf50;} .bar-amber{background:#ffa000;} .bar-white{background:#666;}

.card-body{padding:14px 16px;}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.card-meta{display:flex;align-items:center;gap:8px;}
.card-name{font-size:13px;font-weight:500;}
.card-badge{font-size:10px;border-radius:5px;padding:2px 8px;border:1px solid transparent;}
.badge-purple{background:#1f0f35;color:#ce93d8;border-color:#4a1f70;}
.badge-red{background:#2a1010;color:#ef9a9a;border-color:#5a2020;}
.badge-blue{background:#0d2040;color:#90caf9;border-color:#1e4080;}
.badge-green{background:#0d2510;color:#a5d6a7;border-color:#1a5025;}
.badge-amber{background:#251800;color:#ffe082;border-color:#503000;}
.badge-white{background:#1a1c25;color:#aaa;border-color:#3a3d4a;}
.card-model{font-size:10px;font-family:'JetBrains Mono',monospace;}
.cm-purple{color:#4a1f6a;} .cm-red{color:#7a3030;} .cm-blue{color:#1e4a80;}
.cm-green{color:#1a5c20;} .cm-amber{color:#5c4000;} .cm-white{color:#444;}
.card-text{font-size:13px;line-height:1.75;}
.ct-purple{color:#c0a0d0;} .ct-red{color:#d4a0a0;} .ct-blue{color:#9ab8d8;}
.ct-green{color:#90c090;} .ct-amber{color:#d4b870;} .ct-white{color:#aaa;}

.coordinator-card { border-radius:12px; overflow:hidden; margin-top:1.5rem; border:2px solid #2a2d3a; background:#0d0f14; }
.coordinator-header { background:#13151c; padding:12px 16px; display:flex; align-items:center; gap:10px; border-bottom:1px solid #2a2d3a; }
.coordinator-title { font-size:14px; font-weight:600; color:#e0e0e0; }
.coordinator-sub { font-size:11px; color:#666; margin-left:auto; }
.coordinator-body { padding:16px; }
.coordinator-text { font-size:13px; line-height:1.85; color:#bbb; white-space:pre-wrap; }

.divider{border:none;border-top:1px solid #1e2535;margin:1.5rem 0;}
.status-bar{display:flex;align-items:center;gap:6px;font-size:11px;color:#555;margin-top:1rem;}
.sdot{width:5px;height:5px;border-radius:50%;background:#4caf50;}
</style>
""", unsafe_allow_html=True)

COLOR_CONFIG = {
    "purple": {"pill":"pill-purple","pn":"pn-purple","pr":"pr-purple","pm":"pm-purple","dot":"dot-purple","card":"card-purple","bar":"bar-purple","badge":"badge-purple","cm":"cm-purple","ct":"ct-purple"},
    "red":    {"pill":"pill-red",   "pn":"pn-red",   "pr":"pr-red",   "pm":"pm-red",   "dot":"dot-red",   "card":"card-red",   "bar":"bar-red",   "badge":"badge-red",   "cm":"cm-red",   "ct":"ct-red"},
    "blue":   {"pill":"pill-blue",  "pn":"pn-blue",  "pr":"pr-blue",  "pm":"pm-blue",  "dot":"dot-blue",  "card":"card-blue",  "bar":"bar-blue",  "badge":"badge-blue",  "cm":"cm-blue",  "ct":"ct-blue"},
    "green":  {"pill":"pill-green", "pn":"pn-green", "pr":"pr-green", "pm":"pm-green", "dot":"dot-green", "card":"card-green", "bar":"bar-green", "badge":"badge-green", "cm":"cm-green", "ct":"ct-green"},
    "amber":  {"pill":"pill-amber", "pn":"pn-amber", "pr":"pr-amber", "pm":"pm-amber", "dot":"dot-amber", "card":"card-amber", "bar":"bar-amber", "badge":"badge-amber", "cm":"cm-amber", "ct":"ct-amber"},
    "white":  {"pill":"pill-white", "pn":"pn-white", "pr":"pr-white", "pm":"pm-white", "dot":"dot-white", "card":"card-white", "bar":"bar-white", "badge":"badge-white", "cm":"cm-white", "ct":"ct-white"},
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
st.markdown('<div class="app-sub">6 uzman ajan girişim fikrinizi analiz eder — koordinatör tüm görüşleri toplayıp sonuç raporu çıkarır.</div>', unsafe_allow_html=True)

grid_html = '<div class="agents-grid">'
for name, cfg in AGENTS.items():
    c = COLOR_CONFIG[cfg["color"]]
    grid_html += f"""
    <div class="agent-pill {c['pill']}">
        <div class="pill-top">
            <span class="pill-name {c['pn']}">{cfg['emoji']} {cfg['role']}</span>
            <span class="dot {c['dot']}"></span>
        </div>
        <span class="pill-model {c['pm']}">{cfg['model_type']}</span>
    </div>"""
c = COLOR_CONFIG["white"]
grid_html += f"""
    <div class="agent-pill pill-white">
        <div class="pill-top">
            <span class="pill-name pn-white">⚪ Koordinatör</span>
            <span class="dot dot-white"></span>
        </div>
        <span class="pill-model pm-white">groq · sonuç</span>
    </div>"""
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

question = st.text_area("", placeholder="Örnek: Türkiye'de organik bebek maması e-ticaret işi kurmak istiyorum.", height=100)

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

        with st.spinner("⚪ Koordinatör sonuç raporu hazırlıyor..."):
            coordinator_response = asyncio.run(
                get_coordinator_response(groq_key, question, previous_text)
            )

        st.markdown(f"""
        <div class="coordinator-card">
            <div class="coordinator-header">
                <span style="font-size:16px">⚪</span>
                <span class="coordinator-title">Koordinatör — Sonuç Raporu</span>
                <span class="coordinator-sub">GROQ · özet</span>
            </div>
            <div class="coordinator-body">
                <div class="coordinator-text">{coordinator_response.replace(chr(10), '<br>')}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="status-bar"><span class="sdot"></span>Analiz tamamlandı · 5 uzman + 1 koordinatör</div>', unsafe_allow_html=True)
