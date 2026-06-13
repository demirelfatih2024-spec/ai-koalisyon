import streamlit as st
import asyncio
import json
import base64
import requests
from datetime import datetime

st.set_page_config(page_title="Trading Kontrol Paneli", page_icon="⚡", layout="wide")

# ── ŞİFRE KORUMASI ──────────────────────────────────────────────
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

if not st.session_state.giris_yapildi:
    st.markdown("""
    <style>
    html, body, [class*="css"] { background-color: #0f1117; color: #e8e8e8; }
    .stApp { background-color: #0f1117; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("## 🔐 Trading Bot Paneli")
    sifre = st.text_input("Şifre", type="password", placeholder="Şifrenizi girin...")
    if st.button("Giriş Yap"):
        if sifre == st.secrets.get("PANEL_SIFRE", ""):
            st.session_state.giris_yapildi = True
            st.rerun()
        else:
            st.error("❌ Yanlış şifre!")
    st.stop()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0f1117; color: #e8e8e8; }
.stApp { background-color: #0f1117; }
.metric-card { background:#161b27; border:1px solid #2a3a50; border-radius:12px; padding:16px 20px; margin-bottom:12px; }
.metric-label { font-size:11px; color:#888; letter-spacing:1px; text-transform:uppercase; margin-bottom:4px; }
.metric-value { font-size:24px; font-weight:600; color:#fff; }
.metric-sub { font-size:12px; color:#555; margin-top:2px; }
.positive { color:#4caf50; }
.negative { color:#cc4444; }
.section-header { font-size:13px; font-weight:600; color:#4fc3f7; letter-spacing:1px; text-transform:uppercase; margin:1.5rem 0 0.8rem; border-bottom:1px solid #1e2535; padding-bottom:6px; }
.islem-row { background:#161b27; border:1px solid #2a3a50; border-radius:8px; padding:10px 14px; margin-bottom:6px; display:flex; align-items:center; justify-content:space-between; }
.emir-row { background:#1a1205; border:1px solid #3a2800; border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.badge { font-size:10px; border-radius:4px; padding:2px 8px; font-weight:500; }
.badge-long { background:#0d2510; color:#4caf50; border:1px solid #1a5025; }
.badge-acik { background:#1a2332; color:#4fc3f7; border:1px solid #1e3a5f; }
.badge-kapali { background:#1a1205; color:#ffa000; border:1px solid #3a2800; }
div[data-testid="stSidebar"] { background-color: #0a0d14; border-right: 1px solid #1e2535; }
.stButton > button { background:#378ADD!important; color:#fff!important; font-weight:500!important; border:none!important; border-radius:8px!important; }
.stTextArea textarea, .stTextInput input { background-color:#161b27!important; color:#e8e8e8!important; border:1px solid #2a3a50!important; border-radius:8px!important; }
.stSelectbox > div, .stNumberInput > div { background-color:#161b27!important; }
</style>
""", unsafe_allow_html=True)

# GitHub bağlantısı
try:
    GH_TOKEN = st.secrets["GH_TOKEN"]
    REPO = "demirelfatih2024-spec/trading-bot"
except:
    GH_TOKEN = ""
    REPO = "demirelfatih2024-spec/trading-bot"

# OKX bağlantısı
try:
    OKX_API_KEY = st.secrets["OKX_API_KEY"]
    OKX_SECRET_KEY = st.secrets["OKX_SECRET_KEY"]
    OKX_PASSPHRASE = st.secrets["OKX_PASSPHRASE"]
except:
    OKX_API_KEY = ""
    OKX_SECRET_KEY = ""
    OKX_PASSPHRASE = ""

def gh_oku(dosya):
    try:
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{dosya}", headers=headers)
        if r.status_code != 200:
            return None, None
        return json.loads(base64.b64decode(r.json()["content"]).decode()), r.json()["sha"]
    except:
        return None, None

def gh_yaz(dosya, veri, sha=None):
    try:
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        icerik = base64.b64encode(json.dumps(veri, ensure_ascii=False, indent=2).encode()).decode()
        data = {"message": f"{dosya} güncellendi", "content": icerik}
        if sha:
            data["sha"] = sha
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{dosya}", headers=headers, json=data)
        return r.status_code in [200, 201]
    except:
        return False

def okx_acik_emirler():
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        emirler = exchange.fetch_open_orders()
        return [{"emir_id": e['id'], "sembol": e['symbol'], "yon": e['side'].upper(),
                 "fiyat": e['price'], "miktar": e['amount'], "dolan": e['filled'],
                 "kalan": e['remaining'], "zaman": e['datetime']} for e in emirler]
    except:
        return []

def okx_emir_iptal(emir_id, sembol):
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        exchange.cancel_order(emir_id, sembol)
        return True
    except:
        return False

def okx_bakiye():
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        b = exchange.fetch_balance()
        return {
            "USDT": float(b['USDT']['free']) if 'USDT' in b and b['USDT']['free'] else 0,
            "BTC": float(b['BTC']['free']) if 'BTC' in b and b['BTC']['free'] else 0,
            "ETH": float(b['ETH']['free']) if 'ETH' in b and b['ETH']['free'] else 0,
        }
    except:
        return {"USDT": 0, "BTC": 0, "ETH": 0}

# Sidebar navigasyon
with st.sidebar:
    st.markdown("### ⚡ Trading Bot")
    st.markdown("---")
    sayfa = st.radio("", [
        "📊 Dashboard",
        "⚙️ Bot Ayarları",
        "🤖 Ajanlar",
        "📋 İşlem Geçmişi",
        "💬 Koalisyon Danışma"
    ], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Çıkış"):
        st.session_state.giris_yapildi = False
        st.rerun()

# ── DASHBOARD ──────────────────────────────────────────────────
if sayfa == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")

    bekleyen, _ = gh_oku("bekleyen_islem.json")
    gecmis, _ = gh_oku("islem_gecmisi.json")
    islemler = gecmis.get("islemler", []) if gecmis else []
    bakiye = okx_bakiye()

    col1, col2, col3, col4 = st.columns(4)
    toplam_islem = len(islemler)
    kar_islemler = [i for i in islemler if float(i.get("kar_zarar", 0)) > 0]
    zarar_islemler = [i for i in islemler if float(i.get("kar_zarar", 0)) < 0]
    toplam_kar = sum(float(i.get("kar_zarar", 0)) for i in islemler)

    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Toplam İşlem</div>
            <div class="metric-value">{toplam_islem}</div><div class="metric-sub">Tüm zamanlar</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Karlı / Zararlı</div>
            <div class="metric-value"><span class="positive">{len(kar_islemler)}</span> / <span class="negative">{len(zarar_islemler)}</span></div>
            <div class="metric-sub">İşlem sonuçları</div></div>""", unsafe_allow_html=True)
    with col3:
        kar_renk = "positive" if toplam_kar >= 0 else "negative"
        kar_isaret = "+" if toplam_kar >= 0 else ""
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Toplam Kar/Zarar</div>
            <div class="metric-value"><span class="{kar_renk}">{kar_isaret}${toplam_kar:.2f}</span></div>
            <div class="metric-sub">USDT</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">OKX Bakiye</div>
            <div class="metric-value">${bakiye['USDT']:.2f}</div><div class="metric-sub">USDT</div></div>""", unsafe_allow_html=True)

    # Açık Pozisyonlar
    st.markdown('<div class="section-header">Açık Pozisyonlar</div>', unsafe_allow_html=True)
    try:
        import ccxt
        exchange_poz = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        pozisyonlar = exchange_poz.fetch_positions()
        acik_pozlar = [p for p in pozisyonlar if p['contracts'] and float(p['contracts']) > 0]
        if acik_pozlar:
            for poz in acik_pozlar:
                giris = float(poz['entryPrice'] or 0)
                anlık = float(poz['markPrice'] or 0)
                kar_zarar = float(poz['unrealizedPnl'] or 0)
                kar_yuzde = ((anlık - giris) / giris * 100) if giris > 0 else 0
                kar_renk = "#4caf50" if kar_zarar >= 0 else "#cc4444"
                kar_isaret = "+" if kar_zarar >= 0 else ""
                col_poz, col_kapat = st.columns([4, 1])
                with col_poz:
                    st.markdown(f"""<div class="emir-row">
                        <div style="font-weight:600;color:#e8e8e8;">{poz['symbol']} — {poz['side'].upper()} {poz['leverage']}x</div>
                        <div style="font-size:11px;color:#888;margin-top:4px;">Giriş: {giris} | Anlık: {anlık} | Miktar: {poz['contracts']}</div>
                        <div style="margin-top:4px;"><span style="color:{kar_renk};font-weight:600;">{kar_isaret}${kar_zarar:.4f} ({kar_isaret}{kar_yuzde:.2f}%)</span></div>
                    </div>""", unsafe_allow_html=True)
                with col_kapat:
                    if st.button("🔴 Kapat", key=f"kapat_{poz['symbol']}"):
                        try:
                            kapat_yon = 'sell' if poz['side'].upper() == 'LONG' else 'buy'
                            exchange_poz.create_order(symbol=poz['symbol'], type='market', side=kapat_yon,
                                amount=poz['contracts'], params={'tdMode': 'cross', 'reduceOnly': True})
                            st.success("✅ Pozisyon kapatıldı!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Hata: {e}")
        else:
            st.info("Açık pozisyon yok.")
    except:
        st.info("Pozisyon verisi alınamadı.")

    # Açık Emirler
    st.markdown('<div class="section-header">Açık Emirler</div>', unsafe_allow_html=True)
    acik_emirler = okx_acik_emirler()
    if acik_emirler:
        for emir in acik_emirler:
            col_emir, col_iptal = st.columns([4, 1])
            with col_emir:
                st.markdown(f"""<div class="emir-row">
                    <div style="font-weight:600;color:#e8e8e8;">{emir['sembol']} — {emir['yon']}</div>
                    <div style="font-size:11px;color:#888;margin-top:4px;">Fiyat: {emir['fiyat']} | Miktar: {emir['miktar']} | Kalan: {emir['kalan']}</div>
                    <div style="font-size:11px;color:#555;">{emir['zaman']}</div>
                </div>""", unsafe_allow_html=True)
            with col_iptal:
                if st.button("❌ İptal", key=f"iptal_{emir['emir_id']}"):
                    if okx_emir_iptal(emir['emir_id'], emir['sembol']):
                        st.success("✅ Emir iptal edildi!")
                        st.rerun()
                    else:
                        st.error("❌ İptal başarısız!")
    else:
        st.info("Açık emir yok.")

    # Son işlemler
    st.markdown('<div class="section-header">Son İşlemler</div>', unsafe_allow_html=True)
    if islemler:
        for i in reversed(islemler[-5:]):
            kz = float(i.get("kar_zarar", 0))
            kz_str = f"+${kz:.2f}" if kz > 0 else f"${kz:.2f}"
            kz_renk = "#4caf50" if kz > 0 else "#cc4444" if kz < 0 else "#888"
            st.markdown(f"""<div class="islem-row">
                <div><span style="font-weight:500;color:#e8e8e8;">{i.get('sembol','N/A')}</span>
                <span class="badge badge-long" style="margin-left:8px;">{i.get('yon','LONG')}</span></div>
                <div style="text-align:right;"><div style="color:{kz_renk};font-weight:600;">{kz_str} USDT</div>
                <div style="font-size:11px;color:#555;">{i.get('zaman','')}</div></div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Henüz işlem geçmişi yok.")

# ── BOT AYARLARI ────────────────────────────────────────────────
elif sayfa == "⚙️ Bot Ayarları":
    st.markdown("## ⚙️ Bot Ayarları")
    config, sha = gh_oku("config.json")
    if config is None:
        config = {"koalisyon_saat_araligi": 6, "max_kaldirac": 10, "max_pozisyon_usdt": 50,
                  "min_hacim_usdt": 1000000, "max_fiyat_usdt": 10, "bot_aktif": True, "onay_zorunlu": True}

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Genel Ayarlar</div>', unsafe_allow_html=True)
        bot_aktif = st.toggle("Bot Aktif", value=config.get("bot_aktif", True))
        onay_zorunlu = st.toggle("Onay Zorunlu", value=config.get("onay_zorunlu", True))
        koalisyon_saat = st.selectbox("Koalisyon Toplantı Sıklığı", [2, 4, 6, 8, 12, 24],
            index=[2,4,6,8,12,24].index(config.get("koalisyon_saat_araligi", 6)))
    with col2:
        st.markdown('<div class="section-header">İşlem Ayarları</div>', unsafe_allow_html=True)
        max_kaldirac = st.slider("Max Kaldıraç", 1, 20, config.get("max_kaldirac", 10))
        max_pozisyon = st.number_input("Max Pozisyon (USDT)", 5, 1000, int(config.get("max_pozisyon_usdt", 50)))
        min_hacim = st.number_input("Min Hacim (USDT)", 100000, 100000000, int(config.get("min_hacim_usdt", 1000000)), step=100000)
        max_fiyat = st.number_input("Max Coin Fiyatı (USDT)", 0.001, 1000.0, float(config.get("max_fiyat_usdt", 10.0)))

    if st.button("💾 Ayarları Kaydet"):
        yeni_config = {**config, "bot_aktif": bot_aktif, "onay_zorunlu": onay_zorunlu,
                       "koalisyon_saat_araligi": koalisyon_saat, "max_kaldirac": max_kaldirac,
                       "max_pozisyon_usdt": max_pozisyon, "min_hacim_usdt": min_hacim, "max_fiyat_usdt": max_fiyat}
        if gh_yaz("config.json", yeni_config, sha):
            st.success("✅ Ayarlar kaydedildi!")
        else:
            st.error("❌ Kayıt başarısız!")

# ── AJANLAR ─────────────────────────────────────────────────────
elif sayfa == "🤖 Ajanlar":
    st.markdown("## 🤖 Ajan Karakterleri")
    config, sha = gh_oku("config.json")
    if config is None:
        config = {}
    ajanlar = config.get("ajanlar", {
        "Stratejist": "Sen Stratejist'sin. Piyasa koşullarını değerlendir. Max 3 cümle. Türkçe yaz.",
        "Analist": "Sen Analist'sin. Teknik verileri yorumla. Max 3 cümle. Türkçe yaz.",
        "Risk": "Sen Risk'sin. Riskleri değerlendir. Max 3 cümle. Türkçe yaz.",
        "Momentum": "Sen Momentum'sun. Zamanlamayı değerlendir. Max 3 cümle. Türkçe yaz.",
        "Quant": "Sen Quant'sın. Pozisyon hesapla. Max 3 cümle. Türkçe yaz.",
        "Orion": "Sen Orion'sun. Final kararı ver. Türkçe yaz."
    })
    emojiler = {"Stratejist": "🟣", "Analist": "🔵", "Risk": "🔴", "Momentum": "🟢", "Quant": "🟡", "Orion": "⚪"}
    yeni_ajanlar = {}
    for ajan, sistem in ajanlar.items():
        emoji = emojiler.get(ajan, "🤖")
        st.markdown(f"**{emoji} {ajan}**")
        yeni_ajanlar[ajan] = st.text_area(f"{ajan} karakteri", value=sistem, height=100,
            key=f"ajan_{ajan}", label_visibility="collapsed")
        st.markdown("---")
    if st.button("💾 Karakterleri Kaydet"):
        yeni_config = {**config, "ajanlar": yeni_ajanlar}
        if gh_yaz("config.json", yeni_config, sha):
            st.success("✅ Karakterler kaydedildi!")
        else:
            st.error("❌ Kayıt başarısız!")

# ── İŞLEM GEÇMİŞİ ──────────────────────────────────────────────
elif sayfa == "📋 İşlem Geçmişi":
    st.markdown("## 📋 İşlem Geçmişi")
    gecmis, _ = gh_oku("islem_gecmisi.json")
    islemler = gecmis.get("islemler", []) if gecmis else []
    if islemler:
        toplam_kar = sum(float(i.get("kar_zarar", 0)) for i in islemler)
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Toplam İşlem", len(islemler))
        with col2: st.metric("Karlı İşlem", len([i for i in islemler if float(i.get("kar_zarar",0)) > 0]))
        with col3: st.metric("Toplam K/Z", f"${toplam_kar:.2f}")
        st.markdown("---")
        for i in reversed(islemler):
            kz = float(i.get("kar_zarar", 0))
            kz_str = f"+${kz:.2f}" if kz > 0 else f"${kz:.2f}"
            kz_renk = "#4caf50" if kz > 0 else "#cc4444" if kz < 0 else "#888"
            st.markdown(f"""<div class="islem-row">
                <div><div style="font-weight:600;color:#e8e8e8;margin-bottom:4px;">{i.get('sembol','N/A')} — {i.get('tip','spot').upper()} {i.get('yon','LONG')}</div>
                <div style="font-size:11px;color:#555;">Giriş: {i.get('giris','N/A')} | TP: {i.get('tp','N/A')} | SL: {i.get('sl','N/A')} | Kaldıraç: {i.get('kaldirac',1)}x</div></div>
                <div style="text-align:right;"><div style="color:{kz_renk};font-weight:600;font-size:16px;">{kz_str}</div>
                <div style="font-size:11px;color:#555;">{i.get('zaman','')}</div>
                <span class="badge badge-{'acik' if i.get('durum')=='ACIK' else 'kapali'}">{i.get('durum','N/A')}</span></div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Henüz işlem geçmişi yok.")

# ── KOALİSYON DANIŞMA ───────────────────────────────────────────
elif sayfa == "💬 Koalisyon Danışma":
    from agents import AGENTS, get_agent_response, get_coordinator_initial, get_coordinator_followup, get_clients, process_coordinator_response, GROQ_RATE_LIMIT_MSG
    from pdf_report import generate_pdf

    COLOR_CONFIG = {
        "purple": {"pill":"pill-purple","pn":"pn-purple","pm":"pm-purple","dot":"dot-purple","card":"card-purple","bar":"bar-purple","badge":"badge-purple","cm":"cm-purple","ct":"ct-purple"},
        "red":    {"pill":"pill-red","pn":"pn-red","pm":"pm-red","dot":"dot-red","card":"card-red","bar":"bar-red","badge":"badge-red","cm":"cm-red","ct":"ct-red"},
        "blue":   {"pill":"pill-blue","pn":"pn-blue","pm":"pm-blue","dot":"dot-blue","card":"card-blue","bar":"bar-blue","badge":"badge-blue","cm":"cm-blue","ct":"ct-blue"},
        "green":  {"pill":"pill-green","pn":"pn-green","pm":"pm-green","dot":"dot-green","card":"card-green","bar":"bar-green","badge":"badge-green","cm":"cm-green","ct":"ct-green"},
        "amber":  {"pill":"pill-amber","pn":"pn-amber","pm":"pm-amber","dot":"dot-amber","card":"card-amber","bar":"bar-amber","badge":"badge-amber","cm":"cm-amber","ct":"ct-amber"},
        "white":  {"pill":"pill-white","pn":"pn-white","pm":"pm-white","dot":"dot-white","card":"card-white","bar":"bar-white","badge":"badge-white","cm":"cm-white","ct":"ct-white"},
    }

    try:
        ANTHROPIC_KEY = st.secrets["ANTHROPIC_API_KEY"]
        GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
    except KeyError as e:
        st.error(f"❌ Secrets eksik: {e}")
        st.stop()

    claude_client, groq_key = get_clients(ANTHROPIC_KEY, GROQ_KEY)

    for key, default in [("phase","input"),("chat_history",[]),("chat_messages",[]),
                         ("agent_cards",[]),("question",""),("agent_responses",[]),("coord_summary","")]:
        if key not in st.session_state:
            st.session_state[key] = default

    def render_agent_card(name, config, response):
        c = COLOR_CONFIG[config["color"]]
        return f"""<div class="agent-card {c['card']}"><div class="card-bar {c['bar']}"></div><div class="card-body">
            <div class="card-header"><div class="card-meta"><span class="dot {c['dot']}"></span>
            <span class="card-name {c['pn']}">{config.get('name',name)} · {config['role']}</span>
            <span class="card-badge {c['badge']}">{config['model_type'].upper()}</span></div></div>
            <p class="card-text {c['ct']}">{response.replace(chr(10),'<br>')}</p></div></div>"""

    def render_coordinator_card(title, content):
        return f"""<div class="coordinator-card"><div class="coordinator-header">
            <span style="font-size:16px">⚪</span><span class="coordinator-title">{title}</span>
            <span class="coordinator-sub">Claude</span></div>
            <div class="coordinator-body"><div class="coordinator-text">{content.replace(chr(10),'<br>')}</div></div></div>"""

    st.markdown("## 💬 Koalisyon Danışma Paneli")

    if st.session_state.phase == "input":
        question = st.text_area("", placeholder="Soru sorun...", height=100)
        if st.button("⚡ Analizi Başlat"):
            if question.strip():
                st.session_state.question = question
                st.session_state.phase = "analysis"
                st.rerun()
            else:
                st.warning("Lütfen bir soru girin.")

    elif st.session_state.phase == "analysis":
        q = st.session_state.question
        previous_text = ""
        agent_cards_html = []
        agent_responses_list = []
        for name, config in AGENTS.items():
            with st.spinner(f"{config['emoji']} {config['role']} değerlendiriyor..."):
                response = asyncio.run(get_agent_response(claude_client, groq_key, name, config, q, previous_text))
            if response == GROQ_RATE_LIMIT_MSG:
                card_html = f"<div style='border:1px solid #4a3800;background:#1f1708;padding:12px;border-radius:8px;margin-bottom:8px;'><span style='color:#ffa000;'>⚠️ {config['role']} — limit doldu</span></div>"
                previous_text += f"\n{config['role']}: [limit]\n"
            else:
                card_html = render_agent_card(name, config, response)
                previous_text += f"\n{config['role']}: {response}\n"
            agent_responses_list.append((config["role"], response if response != GROQ_RATE_LIMIT_MSG else "[Limit]"))
            agent_cards_html.append(card_html)
            st.markdown(card_html, unsafe_allow_html=True)
        st.session_state.agent_cards = agent_cards_html
        st.session_state.agent_responses = agent_responses_list
        with st.spinner("⚪ Koordinatör rapor hazırlıyor..."):
            coord_raw = asyncio.run(get_coordinator_initial(claude_client, q, previous_text))
            coord_response = asyncio.run(process_coordinator_response(claude_client, groq_key, coord_raw, previous_text))
        st.session_state.coord_summary = coord_response
        st.markdown(render_coordinator_card("Koordinatör — İlk Rapor", coord_response), unsafe_allow_html=True)
        st.session_state.chat_history = [{"role": "assistant", "content": f"Uzman görüşleri:\n{previous_text}\n\nKoordinatör:\n{coord_response}"}]
        st.session_state.chat_messages = [("coord_initial", coord_response)]
        st.session_state.phase = "chat"
        st.rerun()

    elif st.session_state.phase == "chat":
        for card_html in st.session_state.agent_cards:
            st.markdown(card_html, unsafe_allow_html=True)
        for msg_type, content in st.session_state.chat_messages:
            if msg_type in ("coord_initial", "coord"):
                label = "Koordinatör — İlk Rapor" if msg_type == "coord_initial" else "Koordinatör"
                st.markdown(render_coordinator_card(label, content), unsafe_allow_html=True)
            elif msg_type == "user":
                st.markdown(f'<div class="chat-user"><div class="chat-label">SEN</div>{content}</div>', unsafe_allow_html=True)
        user_input = st.text_area("Devam et:", height=80, key=f"chat_{len(st.session_state.chat_messages)}")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            if st.button("💬 Gönder"):
                if user_input.strip():
                    with st.spinner("⚪ Koordinatör yanıtlıyor..."):
                        coord_raw = asyncio.run(get_coordinator_followup(claude_client, groq_key, st.session_state.chat_history, user_input))
                        context = st.session_state.chat_history[-1]["content"] if st.session_state.chat_history else ""
                        coord_response = asyncio.run(process_coordinator_response(claude_client, groq_key, coord_raw, context))
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    st.session_state.chat_history.append({"role": "assistant", "content": coord_response})
                    st.session_state.chat_messages.append(("user", user_input))
                    st.session_state.chat_messages.append(("coord", coord_response))
                    st.session_state.coord_summary = coord_response
                    st.rerun()
        with col2:
            if st.button("📄 PDF"):
                with st.spinner("PDF hazırlanıyor..."):
                    pdf_bytes = generate_pdf(question=st.session_state.question,
                        agent_responses=st.session_state.get("agent_responses", []),
                        chat_messages=st.session_state.get("chat_messages", []),
                        coord_summary=st.session_state.get("coord_summary", ""))
                st.download_button("⬇️ İndir", pdf_bytes, "rapor.pdf", "application/pdf")
        with col3:
            if st.button("🔄 Yeni"):
                for key in ["phase","chat_history","chat_messages","agent_cards","question","agent_responses","coord_summary"]:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
