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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: var(--color-background-tertiary, #f5f5f5); }

/* Sidebar - agresif override */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div,
[data-testid="stSidebar"] section,
[data-testid="stSidebarContent"],
.st-emotion-cache-1cypcdb,
.st-emotion-cache-6tkfeg {
    background-color: #130f2a !important;
    border-right: 0.5px solid rgba(127,119,221,0.2) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: rgba(255,255,255,0.55) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-size: 13px !important;
    padding: 4px 0 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    color: #b3aeee !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(127,119,221,0.15) !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(127,119,221,0.15) !important;
    color: rgba(255,255,255,0.6) !important;
    border: 0.5px solid rgba(127,119,221,0.3) !important;
    font-size: 13px !important;
}

/* Butonlar */
.stButton > button {
    background: #7F77DD !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}
.stButton > button:hover { background: #6b63cc !important; }

/* Input alanları */
.stTextArea textarea, .stTextInput input {
    background-color: var(--color-background-secondary, #f0f0f0) !important;
    border: 0.5px solid var(--color-border-tertiary) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
.stSelectbox > div, .stNumberInput > div { border-radius: 8px !important; }

/* Metrik kartlar */
.mcard { border-radius: 10px; padding: 0.875rem 1rem; border: 0.5px solid var(--color-border-tertiary); background: var(--color-background-primary); border-top: 2px solid transparent; margin-bottom: 0; }
.mcard.blue { border-top-color: #7F77DD; }
.mcard.green { border-top-color: #1D9E75; }
.mcard.pos { border-top-color: #1D9E75; background: #E1F5EE; }
.mcard.neg { border-top-color: #E24B4A; background: #FCEBEB; }
.mcard.purple { border-top-color: #534AB7; }
.mlabel { font-size: 10px; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.mval { font-size: 22px; font-weight: 500; color: var(--color-text-primary); }
.mval.g { color: #0F6E56; }
.mval.r { color: #A32D2D; }
.msub { font-size: 11px; color: var(--color-text-tertiary); margin-top: 3px; }

/* Section header */
.section-header { font-size: 11px; font-weight: 500; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin: 1.25rem 0 0.5rem; display: flex; align-items: center; gap: 5px; }

/* Pozisyon kartları */
.pos-card { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: 10px; padding: 12px 1rem; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; }
.pos-card.pnl-pos { background: rgba(29,158,117,0.06); border-color: rgba(29,158,117,0.2); }
.pos-card.pnl-neg { background: rgba(226,75,74,0.06); border-color: rgba(226,75,74,0.2); }

/* Coin badge */
.cb { width: 36px; height: 36px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; }
.cb.long { background: #E1F5EE; color: #0F6E56; }
.cb.short { background: #FCEBEB; color: #A32D2D; }

/* Badge */
.badge { display: inline-flex; font-size: 10px; padding: 2px 7px; border-radius: 99px; font-weight: 500; }
.badge-long { background: #E1F5EE; color: #0F6E56; }
.badge-short { background: #FCEBEB; color: #A32D2D; }
.badge-acik { background: #E6F1FB; color: #185FA5; }
.badge-kapali { background: var(--color-background-secondary); color: var(--color-text-tertiary); }

/* İşlem satırı */
.islem-row { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: 10px; padding: 10px 1rem; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
.islem-row.kar { background: rgba(29,158,117,0.05); border-color: rgba(29,158,117,0.15); }
.islem-row.zarar { background: rgba(226,75,74,0.05); border-color: rgba(226,75,74,0.15); }

/* Emir satırı */
.emir-row { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: 10px; padding: 10px 1rem; margin-bottom: 6px; }

/* Ajan kartları */
.ajan-card { background: var(--color-background-primary); border: 0.5px solid var(--color-border-tertiary); border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 8px; }
.ajan-card.orion { border-color: #7F77DD; background: rgba(127,119,221,0.04); }

/* Pozitif / negatif renkler */
.positive { color: #0F6E56 !important; }
.negative { color: #A32D2D !important; }
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

@st.cache_data(ttl=30, show_spinner=False)
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

def acik_pozisyon_sembolleri():
    """Şu an OKX'te gerçekten açık olan futures pozisyonların sembol listesi"""
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        pozisyonlar = exchange.fetch_positions()
        return set(p['symbol'] for p in pozisyonlar if p['contracts'] and float(p['contracts']) > 0)
    except:
        return set()

def kapanan_islemin_kar_zararini_bul(sembol_ccxt, giris_fiyat, yon):
    """
    OKX'ten kapanmış pozisyonun gerçekleşen PnL'ini çekmeye çalışır.
    Önce fetch_my_trades (işlem geçmişi) dener, bulamazsa fetch_closed_orders dener.
    """
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE,
                             'options': {'defaultType': 'swap'}})

        # Yöntem 1: fetch_my_trades — gerçekleşen işlemlerden pnl çek
        try:
            trades = exchange.fetch_my_trades(sembol_ccxt, limit=20)
            toplam_pnl = 0.0
            pnl_bulundu = False
            for t in reversed(trades):
                pnl = t.get('info', {}).get('pnl')
                if pnl is not None and pnl != '0' and pnl != '':
                    toplam_pnl += float(pnl)
                    pnl_bulundu = True
            if pnl_bulundu:
                return round(toplam_pnl, 4)
        except Exception:
            pass

        # Yöntem 2: fetch_closed_orders — kapanmış emirlerden info.pnl çek
        try:
            kapanan = exchange.fetch_closed_orders(sembol_ccxt, limit=20)
            for o in reversed(kapanan):
                if o.get('status') == 'closed' and float(o.get('filled', 0) or 0) > 0:
                    pnl = o.get('info', {}).get('pnl')
                    if pnl is not None and pnl != '0' and pnl != '':
                        return float(pnl)
        except Exception:
            pass

        return None
    except Exception:
        return None

def islem_gecmisini_senkronize_et():
    """
    islem_gecmisi.json'daki durum='ACIK' kayıtları kontrol eder.
    Eğer OKX'te o sembol için artık açık pozisyon yoksa, kapanmış kabul eder
    ve OKX'ten gerçekleşen kâr/zararı çekip kaydı günceller.
    Güncelleme yapıldıysa True, hiçbir değişiklik yoksa False döner.
    """
    gecmis, sha = gh_oku("islem_gecmisi.json")
    if not gecmis:
        return False

    islemler = gecmis.get("islemler", [])
    if not islemler:
        return False

    acik_semboller_okx = acik_pozisyon_sembolleri()
    degisiklik_oldu = False

    for islem in islemler:
        if islem.get("durum") != "ACIK":
            continue

        sembol_ham = islem.get("sembol", "")
        if not sembol_ham:
            continue

        # bekleyen_islem/islem_gecmisi'nde sembol "WLD/USDT" formatında olabilir,
        # futures sembolü ise ccxt'de "WLD/USDT:USDT" şeklinde.
        sembol_futures = sembol_ham if ":USDT" in sembol_ham else sembol_ham + ":USDT"

        if sembol_futures in acik_semboller_okx:
            # Hâlâ açık, dokunma
            continue

        # OKX'te artık açık pozisyon yok -> kapanmış kabul et
        giris_fiyat = float(islem.get("giris", 0) or 0)
        yon = islem.get("yon", "LONG")
        gercek_kz = kapanan_islemin_kar_zararini_bul(sembol_futures, giris_fiyat, yon)

        islem["durum"] = "KAPALI"
        if gercek_kz is not None:
            islem["kar_zarar"] = round(gercek_kz, 4)
        # gercek_kz bulunamadıysa kar_zarar eski değerinde (genelde 0) kalır,
        # ama en azından durum artık KAPALI olarak işaretlenir.
        degisiklik_oldu = True

    if degisiklik_oldu:
        gecmis["islemler"] = islemler
        gh_yaz("islem_gecmisi.json", gecmis, sha)

    return degisiklik_oldu

# Sidebar navigasyon
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.75rem;padding:0 2px;">
        <div style="width:36px;height:36px;background:#7F77DD;border-radius:9px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <polygon points="9,1.5 11,7 17,7 12.5,10.5 14,16 9,12.5 4,16 5.5,10.5 1,7 7,7"
                    stroke="white" stroke-width="1.2" stroke-linejoin="round"
                    fill="rgba(255,255,255,0.2)"/>
                <circle cx="9" cy="9" r="1.8" fill="white"/>
                <line x1="9" y1="0" x2="9" y2="2" stroke="white" stroke-width="1" opacity="0.5"/>
                <line x1="9" y1="16" x2="9" y2="18" stroke="white" stroke-width="1" opacity="0.5"/>
                <line x1="0" y1="9" x2="2" y2="9" stroke="white" stroke-width="1" opacity="0.5"/>
                <line x1="16" y1="9" x2="18" y2="9" stroke="white" stroke-width="1" opacity="0.5"/>
            </svg>
        </div>
        <div>
            <div style="font-size:18px;font-weight:600;color:#ffffff;line-height:1.1;">Orion</div>
            <div style="font-size:11px;color:rgba(179,174,238,0.7);margin-top:1px;">AI Koalisyon</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    sayfa = st.radio("", [
        "📊 Dashboard",
        "⚙️ Bot Ayarları",
        "🤖 Ajanlar",
        "📋 İşlem Geçmişi",
        "💬 Koalisyon Danışma"
    ], label_visibility="collapsed")
    st.markdown("---")
    # Bot durumu
    try:
        from islem_gecmisi import config_oku
        _cfg = config_oku()
        _aktif = "🟢 Bot aktif" if _cfg.get("bot_aktif", True) else "🔴 Bot deaktif"
        _onay = "· Onay kapalı" if not _cfg.get("onay_zorunlu", True) else "· Onay açık"
        st.markdown(f"<div style='font-size:11px;color:rgba(255,255,255,0.35);padding:0 4px;'>{_aktif} {_onay}</div>", unsafe_allow_html=True)
    except:
        pass
    st.markdown("")
    if st.button("🚪 Çıkış"):
        st.session_state.giris_yapildi = False
        st.rerun()

RAILWAY_URL = "https://trading-bot-production-4e70.up.railway.app"

def koalisyonu_tetikle():
    try:
        r = requests.post(f"{RAILWAY_URL}/koalisyon-tetikle", timeout=15)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

# ── DASHBOARD ──────────────────────────────────────────────────
if sayfa == "📊 Dashboard":
    col_baslik, col_buton, col_yenile = st.columns([4, 1, 1])
    with col_baslik:
        st.markdown("## 📊 Dashboard")
    with col_buton:
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("▶ Koalisyonu Topla", use_container_width=True):
            with st.spinner("Koalisyon toplantısı tetikleniyor..."):
                basarili, mesaj = koalisyonu_tetikle()
            if basarili:
                st.toast("✅ Koalisyon toplantısı başlatıldı! Telegram'ı kontrol et.", icon="✅")
            else:
                st.toast(f"❌ Tetikleme başarısız: {mesaj}", icon="❌")
    with col_yenile:
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Kapanan işlemler kontrol ediliyor..."):
        guncellendi = islem_gecmisini_senkronize_et()
    if guncellendi:
        st.toast("📊 Kapanan işlemler güncellendi", icon="✅")

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
        st.markdown(f"""<div class="mcard blue"><div class="mlabel">Toplam İşlem</div>
            <div class="mval">{toplam_islem}</div><div class="msub">Tüm zamanlar</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="mcard green"><div class="mlabel">Karlı / Zararlı</div>
            <div class="mval"><span class="g">{len(kar_islemler)}</span> <span style="color:var(--color-text-tertiary);">/</span> <span class="r">{len(zarar_islemler)}</span></div>
            <div class="msub">İşlem sonuçları</div></div>""", unsafe_allow_html=True)
    with col3:
        kz_class = "pos" if toplam_kar >= 0 else "neg"
        kz_val_class = "g" if toplam_kar >= 0 else "r"
        kar_isaret = "+" if toplam_kar >= 0 else ""
        st.markdown(f"""<div class="mcard {kz_class}"><div class="mlabel">Toplam Kar/Zarar</div>
            <div class="mval {kz_val_class}">{kar_isaret}${toplam_kar:.2f}</div>
            <div class="msub">USDT</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="mcard purple"><div class="mlabel">OKX Bakiye</div>
            <div class="mval">${bakiye['USDT']:.2f}</div><div class="msub">USDT</div></div>""", unsafe_allow_html=True)

    # Açık Pozisyonlar
    st.markdown('<div class="section-header">📊 Açık Pozisyonlar</div>', unsafe_allow_html=True)
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
                    poz_yon = poz['side'].upper()
                    poz_class = "pnl-pos" if kar_zarar >= 0 else "pnl-neg"
                    cb_class = "long" if poz_yon == "LONG" else "short"
                    coin_kisa = poz['symbol'].split('/')[0][:4]
                    badge_class = "badge-long" if poz_yon == "LONG" else "badge-short"
                    st.markdown(f"""<div class="emir-row {poz_class}">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <div class="cb {cb_class}">{coin_kisa}</div>
                            <div>
                                <div style="font-size:13px;font-weight:500;color:var(--color-text-primary);">{poz['symbol']} <span class="badge {badge_class}">{poz_yon} {poz['leverage']}x</span></div>
                                <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:3px;">Giriş: {giris} · Anlık: {anlık} · Miktar: {poz['contracts']}</div>
                                <div style="margin-top:4px;font-size:13px;font-weight:500;color:{kar_renk};">{kar_isaret}${kar_zarar:.4f} ({kar_isaret}{kar_yuzde:.2f}%)</div>
                            </div>
                        </div>
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
    st.markdown('<div class="section-header">🕐 Açık Emirler</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="section-header">📋 Son İşlemler</div>', unsafe_allow_html=True)
    if islemler:
        for i in reversed(islemler[-5:]):
            kz = float(i.get("kar_zarar", 0))
            kz_str = f"+${kz:.2f}" if kz > 0 else f"${kz:.2f}"
            kz_renk = "#0F6E56" if kz > 0 else "#A32D2D" if kz < 0 else "var(--color-text-tertiary)"
            islem_class = "islem-row kar" if kz > 0 else "islem-row zarar" if kz < 0 else "islem-row"
            yon = i.get('yon','LONG')
            badge_cls = "badge-long" if yon == "LONG" else "badge-short"
            coin_kisa = i.get('sembol','N/A').split('/')[0][:4]
            cb_cls = "long" if yon == "LONG" else "short"
            st.markdown(f"""<div class="{islem_class}">
                <div style="display:flex;align-items:center;gap:8px;">
                    <div class="cb {cb_cls}" style="width:28px;height:28px;font-size:9px;">{coin_kisa}</div>
                    <div>
                        <div style="font-size:13px;font-weight:500;color:var(--color-text-primary);">{i.get('sembol','N/A')}</div>
                        <div style="font-size:11px;color:var(--color-text-tertiary);">{i.get('zaman','')}</div>
                    </div>
                    <span class="badge {badge_cls}">{yon}</span>
                </div>
                <div style="font-size:13px;font-weight:500;color:{kz_renk};">{kz_str}</div>
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
        max_pozisyon = st.number_input("Max Pozisyon Limiti (USDT)", 5, 1000, int(config.get("max_pozisyon_usdt", 50)))
        min_hacim = st.number_input("Min Hacim (USDT)", 100000, 100000000, int(config.get("min_hacim_usdt", 1000000)), step=100000)
        max_fiyat = st.number_input("Max Coin Fiyatı (USDT)", 0.001, 1000.0, float(config.get("max_fiyat_usdt", 10.0)))
        min_pozisyon = st.number_input(
            "Minimum Pozisyon (USDT)", 1, 100, int(config.get("min_pozisyon_usdt", 8)),
            help="Hesaplanan pozisyon bunun altında kalırsa otomatik bu seviyeye yükseltilir (komisyona gitmesin diye)."
        )
        st.markdown("**TP / SL Hedefleri**")
        col_tp, col_sl = st.columns(2)
        with col_tp:
            tp_hedef = st.number_input(
                "TP Hedefi (%)", 0.5, 10.0,
                float(config.get("tp_hedef_yuzde", 2.0)),
                step=0.1, format="%.1f",
                help="Giriş fiyatından ham fiyat farkı. Kod tarafında otomatik hesaplanır."
            )
        with col_sl:
            sl_hedef = st.number_input(
                "SL Hedefi (%)", 0.5, 15.0,
                float(config.get("sl_hedef_yuzde", 3.0)),
                step=0.1, format="%.1f",
                help="Giriş fiyatından ham fiyat farkı. TP'den biraz geniş tutulması önerilir."
            )
        pozisyon_yuzde = st.slider(
            "Pozisyon Yüzdesi (Bileşik Kazanç)", 5, 90,
            int(config.get("pozisyon_yuzde", 0.35) * 100), step=5, format="%d%%"
        )
        guncel_bakiye = okx_bakiye()
        tahmini = round(guncel_bakiye["USDT"] * (pozisyon_yuzde / 100), 2)
        st.caption(f"💡 Anlık bakiye ${guncel_bakiye['USDT']:.2f} → Tahmini pozisyon: ${tahmini} USDT")

    if st.button("💾 Ayarları Kaydet"):
        yeni_config = {**config, "bot_aktif": bot_aktif, "onay_zorunlu": onay_zorunlu,
                       "koalisyon_saat_araligi": koalisyon_saat, "max_kaldirac": max_kaldirac,
                       "max_pozisyon_usdt": max_pozisyon, "min_hacim_usdt": min_hacim,
                       "max_fiyat_usdt": max_fiyat, "min_pozisyon_usdt": min_pozisyon,
                       "tp_hedef_yuzde": tp_hedef, "sl_hedef_yuzde": sl_hedef,
                       "pozisyon_yuzde": round(pozisyon_yuzde / 100, 2)}
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
