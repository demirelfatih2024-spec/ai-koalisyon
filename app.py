import streamlit as st
import asyncio
import json
import base64
import requests
from datetime import datetime, timezone

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

def kapanan_islemi_coz(sembol_ccxt, emir_id):
    """
    PnL eşleştirmesini SEMBOL üzerinden değil, benzersiz EMİR ID (ordId) üzerinden yapar.

    Eski sürüm sadece sembole bakıp 'o sembolün en son PnL'ini' her kayda yazıyordu;
    bu yüzden aynı sembolün farklı işlemleri (örn. SNXX'in 9 ayrı işlemi) aynı PnL'i
    taşıyordu. Artık kayıttaki emir_id'nin gerçekten dolduğu AN'ı buluyor, sonra o anı
    kapsayan kapanmış pozisyonun PnL'ini döndürüyoruz.

    Dönüş: (durum, kar_zarar)
      ("KAPALI", float) → pozisyon açılıp kapandı, PnL kesin
      ("IPTAL",  0.0)   → emir hiç dolmadı, iptal/red edildi
      (None,     None)  → eşleştirilemedi → UYDURMA VERİ YAZMA, kayıt ACIK kalsın
    """
    if not emir_id:
        return None, None
    try:
        import ccxt
        ex = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE,
                       'options': {'defaultType': 'swap'}})
    except Exception:
        return None, None

    # 1) Emrin kendisi: doldu mu, ne zaman doldu?
    try:
        emir = ex.fetch_order(str(emir_id), sembol_ccxt)
    except Exception as e:
        print(f"fetch_order başarısız ({emir_id}): {e}")
        return None, None

    dolan = float(emir.get('filled') or 0)
    if dolan <= 0:
        if emir.get('status') in ('canceled', 'expired', 'rejected'):
            return "IPTAL", 0.0
        return None, None      # hâlâ bekliyor olabilir → dokunma

    dolum_ms = int(emir.get('lastTradeTimestamp') or emir.get('timestamp') or 0)
    if not dolum_ms:
        return None, None

    # 2) Bu dolumu ZAMAN OLARAK kapsayan kapanmış pozisyonu bul
    try:
        gecmis = ex.fetch_positions_history([sembol_ccxt], limit=50)
    except Exception as e:
        print(f"positions_history başarısız ({sembol_ccxt}): {e}")
        return None, None

    for p in gecmis:
        info = p.get('info', {}) or {}
        try:
            acilis = int(info.get('cTime') or 0)
            kapanis = int(info.get('uTime') or 0)
        except (TypeError, ValueError):
            continue
        if not acilis or not kapanis:
            continue
        if acilis - 60000 <= dolum_ms <= kapanis + 60000:   # ±60 sn tolerans
            pnl = info.get('realizedPnl')
            if pnl is None:
                pnl = info.get('pnl')
            if pnl is None:
                return None, None
            return "KAPALI", round(float(pnl), 4)

    return None, None       # dolum var ama kapanmış pozisyon yok → muhtemelen hâlâ açık

def acik_emir_sembolleri():
    """OKX'te bekleyen (dolmamış) limit emirlerin sembol listesi"""
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE})
        emirler = exchange.fetch_open_orders()
        return set(e['symbol'].replace(':USDT', '') for e in emirler)
    except:
        return set()

def okx_gecmis_islemleri_ice_aktar(bas_ms=None, bit_ms=None):
    """
    OKX'teki kapanmış vadeli pozisyonları çeker ve islem_gecmisi.json'a ekler.
    bas_ms / bit_ms (ms epoch) verilirse SADECE o tarih aralığında (kapanış
    zamanı = uTime) kapanan işlemler eklenir. Verilmezse son 100 kayıt.
    """
    try:
        import ccxt
        exchange = ccxt.okx({'apiKey': OKX_API_KEY, 'secret': OKX_SECRET_KEY, 'password': OKX_PASSPHRASE,
                             'options': {'defaultType': 'swap'}})
        kapananlar = []
        # OKX 'after=ts' => uTime'i ts'ten ESKİ kayıtlar. Bitiş tarihini sabitleyip
        # 100 kayıt geriye gideriz; başlangıç filtresini Python tarafında uygularız.
        _params = {"after": str(bit_ms)} if bit_ms else {}
        try:
            # limit=100: OKX'in tek istekte verdiği azami.
            kapananlar = exchange.fetch_positions_history(None, limit=100, params=_params)
        except Exception:
            pass

        # CCXT boş dönerse veya hata verirse REST API ile doğrudan çek
        if not kapananlar:
            try:
                import time, hashlib, hmac
                timestamp = str(time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())) + '.000Z'
                request_path = '/api/v5/account/positions-history?instType=SWAP&limit=100'
                if bit_ms:
                    request_path += f'&after={bit_ms}'
                message = timestamp + 'GET' + request_path
                signature = base64.b64encode(
                    hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
                ).decode()
                headers = {
                    'OK-ACCESS-KEY': OKX_API_KEY,
                    'OK-ACCESS-SIGN': signature,
                    'OK-ACCESS-TIMESTAMP': timestamp,
                    'OK-ACCESS-PASSPHRASE': OKX_PASSPHRASE,
                    'Content-Type': 'application/json',
                }
                r = requests.get('https://www.okx.com' + request_path, headers=headers, timeout=10)
                if r.status_code == 200:
                    kapananlar = r.json().get("data", [])
            except Exception as e:
                print(f"REST pozisyon hatası: {e}")

        if not kapananlar:
            return 0

        gecmis, sha = gh_oku("islem_gecmisi.json")
        if not gecmis:
            gecmis = {"islemler": []}
            sha = None
        islemler = gecmis.get("islemler", [])
        # KRİTİK: OKX aynı 'posId'yi, aynı sembolde art arda açılan farklı pozisyonlar
        # için TEKRAR kullanabiliyor (kanıt: SNXX LONG ve SHORT ikisi de posId
        # 3794575046693298178). Bu yüzden posId TEK BAŞINA benzersiz DEĞİL.
        # Analiz aracının (_dedupe_positions) doğru mantığıyla hizalıyoruz:
        # benzersiz anahtar = posId + kapanış zaman damgası (uTime).
        def _anahtar(pid, kts):
            return f"{pid}:{kts}"
        mevcut_anahtarlar = {
            _anahtar(i.get("pos_id"), i.get("kapanis_ts"))
            for i in islemler if i.get("pos_id")
        }
        eklenen_sayisi = 0

        for p in kapananlar:
            info = p.get("info", {}) if isinstance(p, dict) and "info" in p else (p if isinstance(p, dict) else {})
            sembol_ham = p.get("symbol", "") or info.get("instId", "")
            if not sembol_ham:
                continue
            sembol = sembol_ham.split(":")[0].replace("-SWAP", "").replace("-USDT", "/USDT")
            pnl_val = info.get("realizedPnl") or info.get("pnl") or info.get("pnlRatio") or p.get("unrealizedPnl")
            kz = float(pnl_val or 0)
            giris = str(info.get("openAvgPx") or p.get("entryPrice") or 0)
            cikis = str(info.get("closeAvgPx") or 0)
            kaldirac = str(info.get("lever") or p.get("leverage") or 1)
            yon = "LONG" if (p.get("side") == "long" or info.get("direction") == "long") else "SHORT"

            # Ham kapanış zaman damgası: hem benzersiz anahtarın parçası hem gösterim.
            kapanis_ts = str(info.get("uTime") or info.get("cTime") or p.get("timestamp") or "")
            if kapanis_ts:
                try:
                    zaman_str = datetime.fromtimestamp(int(kapanis_ts)/1000, timezone.utc).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    zaman_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
            else:
                zaman_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")

            # Tarih aralığı filtresi (kullanıcı seçtiyse): aralık dışını atla.
            try:
                _ts_int = int(kapanis_ts) if kapanis_ts else 0
            except ValueError:
                _ts_int = 0
            if _ts_int and bas_ms and _ts_int < bas_ms:
                continue
            if _ts_int and bit_ms and _ts_int > bit_ms:
                continue

            pos_id = str(info.get("posId") or "")
            anahtar = _anahtar(pos_id, kapanis_ts)
            # Kimliklendirilemeyen veya bu (posId+uTime) kombinasyonu zaten kayıtlıysa atla.
            # posId aynı olsa bile farklı uTime → FARKLI pozisyon, eklenir.
            if not pos_id or anahtar in mevcut_anahtarlar:
                continue

            islemler.append({
                "sembol": sembol,
                "yon": yon,
                "durum": "KAPALI",
                "giris": giris,
                "cikis": cikis,           # eski kod bunu hem tp hem sl'ye yazıyordu (yanıltıcı)
                "kaldirac": kaldirac,
                "kar_zarar": round(kz, 4),
                "pos_id": pos_id,
                "kapanis_ts": kapanis_ts,  # benzersiz anahtarın ikinci parçası
                # GÖREV 0: bu kayıtlar positions-history?instType=SWAP'tan geliyor =
                # FUTURES. Eskiden 'tip' yazılmadığı için panel bunları 'SPOT' gösteriyordu.
                "tip": "futures",
                "zaman": zaman_str
            })
            mevcut_anahtarlar.add(anahtar)
            eklenen_sayisi += 1

        # Sadece gerçekten yeni kayıt varsa yaz (her yenilemede boşuna commit atma).
        if eklenen_sayisi > 0:
            gecmis["islemler"] = islemler[-100:]
            gh_yaz("islem_gecmisi.json", gecmis, sha)
        return eklenen_sayisi
    except Exception as e:
        print(f"OKX İçe aktarma hatası: {e}")
        return 0

def islem_gecmisini_senkronize_et():
    """
    islem_gecmisi.json'daki durum='ACIK' kayıtları kontrol eder ve
    ayrıca OKX'teki kapanmış geçmiş pozisyonları içeri aktarır.
    """
    okx_gecmis_islemleri_ice_aktar()
    gecmis, sha = gh_oku("islem_gecmisi.json")
    if not gecmis:
        return False

    islemler = gecmis.get("islemler", [])
    if not islemler:
        return False

    acik_semboller_okx = acik_pozisyon_sembolleri()
    bekleyen_emirler = acik_emir_sembolleri()
    degisiklik_oldu = False

    for islem in islemler:
        if islem.get("durum") != "ACIK":
            continue

        sembol_ham = islem.get("sembol", "")
        if not sembol_ham:
            continue

        sembol_temiz = sembol_ham.replace(":USDT", "")
        sembol_futures = sembol_temiz + ":USDT" if ":USDT" not in sembol_ham else sembol_ham

        # Hâlâ açık pozisyon var → dokunma
        if sembol_futures in acik_semboller_okx:
            continue

        # Hâlâ bekleyen limit emir var → henüz dolmadı, dokunma
        if sembol_temiz in bekleyen_emirler:
            continue

        # Ne pozisyon ne emir → emir ID'siyle kesin sonucu çöz
        durum, kz = kapanan_islemi_coz(sembol_futures, islem.get("emir_id"))

        if durum == "KAPALI":
            islem["durum"] = "KAPALI"
            islem["kar_zarar"] = kz
            degisiklik_oldu = True
        elif durum == "IPTAL":
            islem["durum"] = "IPTAL"
            islem["kar_zarar"] = 0
            degisiklik_oldu = True
        else:
            # Eşleştirilemedi → UYDURMA VERİ YAZMA. Kayıt ACIK kalır, sonra tekrar denenir.
            print(f"PnL eşleştirilemedi, kayda dokunulmadı: {sembol_temiz} / emir_id={islem.get('emir_id')}")
            continue

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
        "📉 TP/SL Analizi",
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

try:
    RAILWAY_URL = (st.secrets.get("RAILWAY_URL") or "").strip().rstrip("/")
except Exception:
    RAILWAY_URL = ""
if not RAILWAY_URL:
    RAILWAY_URL = "https://trading-bot-production-4e70.up.railway.app"
if not RAILWAY_URL.startswith("http://") and not RAILWAY_URL.startswith("https://"):
    RAILWAY_URL = "https://" + RAILWAY_URL

def koalisyonu_tetikle():
    try:
        r = requests.post(f"{RAILWAY_URL}/koalisyon-tetikle", timeout=20)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, f"Bota ulaşılamadı ({RAILWAY_URL}): {e}"

# ── ORTAK: İşlem geçmişi tarih aralığı (Dashboard + İşlem Geçmişi AYNI ayarı kullanır) ──
# Kullanıcının seçtiği aralık st.session_state'te 'gecmis_bas'/'gecmis_bit' olarak
# saklanır; iki sayfa da bunu okur → tek davranış. Varsayılan: son 30 gün.
def _gecmis_aralik_ms():
    from datetime import datetime as _d, timezone as _z, timedelta as _t
    bugun = _d.now(_z.utc).date()
    bas = st.session_state.get("gecmis_bas") or (bugun - _t(days=30))
    bit = st.session_state.get("gecmis_bit") or bugun
    bas_ms = int(_d(bas.year, bas.month, bas.day, tzinfo=_z.utc).timestamp() * 1000)
    bit_ms = int((_d(bit.year, bit.month, bit.day, tzinfo=_z.utc)
                  + _t(days=1) - _t(milliseconds=1)).timestamp() * 1000)
    return bas_ms, bit_ms

def _islem_zaman_ms(islem):
    kts = islem.get("kapanis_ts")
    if kts:
        try:
            return int(kts)
        except (ValueError, TypeError):
            pass
    from datetime import datetime as _d, timezone as _z
    try:
        # 'zaman' metni UTC olarak saklanır (bot tarafı UTC yazar) — naive .timestamp()
        # sunucu yereline göre yorumlar; açıkça UTC olarak sabitliyoruz (Madde 3).
        return int(_d.strptime(islem.get("zaman", ""), "%d.%m.%Y %H:%M")
                   .replace(tzinfo=_z.utc).timestamp() * 1000)
    except Exception:
        return None

def _araligda_filtrele(islemler, bas_ms, bit_ms):
    """Sadece [bas_ms, bit_ms] aralığında kapanan işlemleri döndürür (yeni→eski sıralı).
    Zamanı okunamayan kayıt güvenli tarafta gösterilir."""
    out = [i for i in islemler
           if (_islem_zaman_ms(i) is None) or (bas_ms <= _islem_zaman_ms(i) <= bit_ms)]
    return sorted(out, key=lambda i: (_islem_zaman_ms(i) or 0), reverse=True)

def _trt_goster(islem):
    """
    İşlem zamanını kullanıcıya TRT (UTC+3) olarak, açık etiketle gösterir (Madde 3).
    İç veri UTC'dir; sadece GÖSTERİM burada TR saatine çevrilir.
    """
    from datetime import datetime as _d, timezone as _z, timedelta as _t
    ms = _islem_zaman_ms(islem)   # UTC ms epoch (kapanis_ts veya UTC 'zaman' metninden)
    if ms is None:
        return islem.get("zaman", "")
    try:
        dt_trt = _d.fromtimestamp(ms / 1000, _z.utc) + _t(hours=3)
        return dt_trt.strftime("%d.%m.%Y %H:%M") + " TRT"
    except Exception:
        return islem.get("zaman", "")

def okx_pozisyon_tpsl():
    """
    Açık pozisyonlara bağlı BEKLEYEN TP/SL (algo/OCO) emirlerini OKX'ten çeker.
    TP/SL, pozisyon nesnesinde DEĞİL ayrı algo emirlerinde durur; bu yüzden
    /trade/orders-algo-pending uçundan okunur.
    Dönüş: { 'SNXX-USDT-SWAP': {'tp': '10.31', 'sl': '9.02'}, ... }
    """
    import time, hmac, hashlib
    sonuc = {}
    try:
        for ord_type in ("oco", "conditional"):
            request_path = f"/api/v5/trade/orders-algo-pending?ordType={ord_type}"
            timestamp = str(time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())) + '.000Z'
            message = timestamp + 'GET' + request_path
            signature = base64.b64encode(
                hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
            ).decode()
            headers = {
                'OK-ACCESS-KEY': OKX_API_KEY,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': OKX_PASSPHRASE,
                'Content-Type': 'application/json',
            }
            r = requests.get('https://www.okx.com' + request_path, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            for o in r.json().get("data", []):
                inst = o.get("instId")
                if not inst:
                    continue
                kayit = sonuc.setdefault(inst, {"tp": "", "sl": ""})
                tp = o.get("tpTriggerPx") or ""
                sl = o.get("slTriggerPx") or ""
                if tp and not kayit["tp"]:
                    kayit["tp"] = tp
                if sl and not kayit["sl"]:
                    kayit["sl"] = sl
    except Exception as e:
        print(f"TP/SL algo okuma hatası: {e}")
    return sonuc

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
            st.cache_data.clear()   # OKX bakiye/pozisyon önbelleğini boşalt → anlık veri
            st.rerun()

    # NOT: Dashboard artık OKX'ten OTOMATİK geçmiş çekmiyor. Eskiden buradaki
    # senkronizasyon her açılışta 100 kapanmış pozisyonu geri getirip 'Temizle'yi
    # anlamsız kılıyordu. Veri yalnızca '📋 İşlem Geçmişi' sayfasındaki butonla,
    # seçilen tarih aralığında çekilir. Dashboard sadece kayıtlı veriyi gösterir.
    bekleyen, _ = gh_oku("bekleyen_islem.json")
    gecmis, _ = gh_oku("islem_gecmisi.json")
    _tum_islemler = gecmis.get("islemler", []) if gecmis else []
    # Kullanıcının seçtiği tarih aralığına göre filtrele (İşlem Geçmişi ile aynı ayar).
    _bas_ms, _bit_ms = _gecmis_aralik_ms()
    islemler = _araligda_filtrele(_tum_islemler, _bas_ms, _bit_ms)
    bakiye = okx_bakiye()

    col1, col2, col3, col4 = st.columns(4)
    # IPTAL olan işlemleri metriklerden çıkar
    gercek_islemler = [i for i in islemler if i.get("durum") != "IPTAL"]
    toplam_islem = len(gercek_islemler)
    kar_islemler = [i for i in gercek_islemler if float(i.get("kar_zarar", 0)) > 0]
    zarar_islemler = [i for i in gercek_islemler if float(i.get("kar_zarar", 0)) < 0]
    toplam_kar = sum(float(i.get("kar_zarar", 0)) for i in gercek_islemler)

    with col1:
        st.markdown(f"""<div class="mcard blue"><div class="mlabel">Toplam İşlem</div>
            <div class="mval">{toplam_islem}</div><div class="msub">Seçili tarih aralığı</div></div>""", unsafe_allow_html=True)
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
        # Açık pozisyonlara bağlı bekleyen TP/SL algo emirlerini bir kez çek.
        _tpsl_map = okx_pozisyon_tpsl()
        if acik_pozlar:
            for poz in acik_pozlar:
                giris = float(poz['entryPrice'] or 0)
                anlık = float(poz['markPrice'] or 0)
                kar_zarar = float(poz['unrealizedPnl'] or 0)
                kar_yuzde = ((anlık - giris) / giris * 100) if giris > 0 else 0
                kar_renk = "#4caf50" if kar_zarar >= 0 else "#cc4444"
                kar_isaret = "+" if kar_zarar >= 0 else ""

                # Pozisyon sembolünü OKX instId'ye çevirip TP/SL'yi eşleştir.
                _inst = poz['symbol'].replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')
                _ts = _tpsl_map.get(_inst, {})
                _tp_px, _sl_px = _ts.get("tp", ""), _ts.get("sl", "")
                if _tp_px or _sl_px:
                    _tp_gos = _tp_px if _tp_px else "yok"
                    _sl_gos = _sl_px if _sl_px else "yok"
                    _koruma_html = (f"<div style='font-size:11px;margin-top:3px;'>"
                                    f"<span style='color:#0F6E56;'>🎯 TP: {_tp_gos}</span> · "
                                    f"<span style='color:#A32D2D;'>🛑 SL: {_sl_gos}</span></div>")
                else:
                    _koruma_html = ("<div style='font-size:11px;margin-top:3px;color:#A32D2D;"
                                    "font-weight:600;'>⚠️ TP/SL YOK — pozisyon korumasız</div>")

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
                                {_koruma_html}
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
        for i in islemler[:5]:   # islemler zaten yeni→eski sıralı ve aralığa göre filtreli
            if i.get("durum") == "IPTAL":
                continue
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
                        <div style="font-size:11px;color:var(--color-text-tertiary);">{_trt_goster(i)}</div>
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
    from datetime import datetime as _dt2, timezone as _tz2, timedelta as _td2
    st.markdown("## 📋 İşlem Geçmişi")

    # (İstek 3) Tarih aralığı seçici — hangi tarihlerdeki işlemlerin çekileceğini
    # kullanıcı belirler. Seçim, Dashboard'un da okuduğu ORTAK ayara yazılır.
    _bugun = _dt2.now(_tz2.utc).date()
    _c1, _c2 = st.columns(2)
    _g_bas = _c1.date_input("Başlangıç tarihi",
                            value=st.session_state.get("gecmis_bas", _bugun - _td2(days=30)),
                            help="Bu tarihten itibaren KAPANAN işlemler. OKX en fazla son 3 ayı verir.")
    _g_bit = _c2.date_input("Bitiş tarihi",
                            value=st.session_state.get("gecmis_bit", _bugun))
    # Ortak ayara yaz — Dashboard aynı aralığı kullansın (tek davranış).
    st.session_state["gecmis_bas"] = _g_bas
    st.session_state["gecmis_bit"] = _g_bit
    st.caption(f"📅 Gösterilen ve çekilecek aralık: **{_g_bas.strftime('%d.%m.%Y')} → "
               f"{_g_bit.strftime('%d.%m.%Y')}** (bu ayar Dashboard'da da geçerli)")

    _b1, _b2, _b3 = st.columns(3)
    if _b1.button("📥 OKX'ten Çek", use_container_width=True):
        _bas_ms = int(_dt2(_g_bas.year, _g_bas.month, _g_bas.day, tzinfo=_tz2.utc).timestamp() * 1000)
        _bit_ms = int((_dt2(_g_bit.year, _g_bit.month, _g_bit.day, tzinfo=_tz2.utc)
                       + _td2(days=1) - _td2(milliseconds=1)).timestamp() * 1000)
        if _bas_ms > _bit_ms:
            st.error("Başlangıç tarihi bitişten sonra olamaz.")
        else:
            with st.spinner("OKX'ten seçilen aralıktaki kapanan işlemler çekiliyor..."):
                eklenen = okx_gecmis_islemleri_ice_aktar(_bas_ms, _bit_ms)
            st.toast(f"✅ {eklenen} yeni kayıt eklendi.", icon="✅")
            st.cache_data.clear()
            st.rerun()
    if _b2.button("🗑️ Temizle", use_container_width=True):
        _, sha = gh_oku("islem_gecmisi.json")
        if gh_yaz("islem_gecmisi.json", {"islemler": []}, sha):
            st.session_state["gecmis_temizlendi"] = True
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("❌ Temizleme başarısız!")
    if _b3.button("🔄 Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.session_state.pop("gecmis_temizlendi", False):
        st.success("✅ İşlem geçmişi temizlendi.")

    # (İstek 2) Sayfa açılışında OTOMATİK veri çekme KALDIRILDI. Veri yalnızca
    # yukarıdaki '📥 OKX'ten Çek' butonuyla çekilir.
    gecmis, _ = gh_oku("islem_gecmisi.json")
    _tum = gecmis.get("islemler", []) if gecmis else []
    # (İstek 1 + tek davranış) Seçili aralığa göre filtrele + yeni→eski sırala.
    _bas_ms, _bit_ms = _gecmis_aralik_ms()
    islemler = _araligda_filtrele(_tum, _bas_ms, _bit_ms)
    if islemler:
        toplam_kar = sum(float(i.get("kar_zarar", 0)) for i in islemler)
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("İşlem (aralıkta)", len(islemler))
        with col2: st.metric("Karlı İşlem", len([i for i in islemler if float(i.get("kar_zarar",0)) > 0]))
        with col3: st.metric("Toplam K/Z", f"${toplam_kar:.2f}")
        st.markdown("---")

        for i in islemler:   # zaten yeni→eski sıralı
            kz = float(i.get("kar_zarar", 0))
            kz_str = f"+${kz:.2f}" if kz > 0 else f"${kz:.2f}"
            kz_renk = "#4caf50" if kz > 0 else "#cc4444" if kz < 0 else "#888"
            st.markdown(f"""<div class="islem-row">
                <div><div style="font-weight:600;color:#e8e8e8;margin-bottom:4px;">{i.get('sembol','N/A')} — {i.get('tip','futures').upper()} {i.get('yon','LONG')}</div>
                <div style="font-size:11px;color:#555;">Giriş: {i.get('giris','N/A')} | TP: {i.get('tp','N/A')} | SL: {i.get('sl','N/A')} | Kaldıraç: {i.get('kaldirac',1)}x</div></div>
                <div style="text-align:right;"><div style="color:{kz_renk};font-weight:600;font-size:16px;">{kz_str}</div>
                <div style="font-size:11px;color:#555;">{_trt_goster(i)}</div>
                <span class="badge badge-{'acik' if i.get('durum')=='ACIK' else 'kapali'}">{i.get('durum','N/A')}</span></div>
            </div>""", unsafe_allow_html=True)
    elif _tum:
        st.info("Seçili tarih aralığında işlem yok. Aralığı genişletin veya '📥 OKX'ten Çek' ile bu aralığı çekin.")
    else:
        st.info("Kayıtlı işlem yok. '📥 OKX'ten Çek' ile seçtiğiniz tarih aralığındaki işlemleri getirin.")

# ── TP/SL ANALİZİ (izole modül) ─────────────────────────────────
# 'okx_tpsl_analyzer' aracı AYRI BİR ALT SÜREÇ (subprocess) olarak çalışır; botun
# karar/emir koduyla hiçbir bağlantısı yoktur, sadece OKX'ten geçmişi OKUR.
# Sonuçlar GitHub'a (analiz_gecmisi.json) KALICI kaydedilir; panel açıldığında en
# son analiz otomatik gösterilir — kullanıcı butona basmak zorunda değildir.
elif sayfa == "📉 TP/SL Analizi":
    import os as _os
    import sys as _sys
    import json as _json
    import subprocess as _subprocess
    from pathlib import Path as _Path
    from datetime import datetime as _dt, timezone as _tz
    import pandas as _pd
    import streamlit.components.v1 as _components

    st.markdown("## 📉 TP/SL İsabet Analizi")
    st.caption("Mevcut TP/SL ayarınız geçmiş işlemlerde kârlı mı çalışmış? Bu sayfa OKX'teki "
               "kapanmış pozisyonları okuyup bunu ölçer. Sadece okur — emir vermez, ayar değiştirmez.")

    # ---- KALICI SAKLAMA: config.json / islem_gecmisi.json ile AYNI yöntem (GitHub) ----
    def _analiz_gecmisi_oku():
        veri, _ = gh_oku("analiz_gecmisi.json")
        return veri.get("analizler", []) if isinstance(veri, dict) else []

    def _analiz_gecmisi_kaydet(snapshot):
        veri, sha = gh_oku("analiz_gecmisi.json")
        analizler = veri.get("analizler", []) if isinstance(veri, dict) else []
        analizler.append(snapshot)
        analizler = analizler[-5:]              # son 5 analizi tut (dosya şişmesin)
        return gh_yaz("analiz_gecmisi.json", {"analizler": analizler}, sha)

    # ---- Analiz aracının klasörü (yerel + deploy) ----
    _buradan = _Path(__file__).resolve().parent
    _adaylar = [_buradan / "okx_tpsl_analyzer", _buradan.parent / "okx_tpsl_analyzer"]
    _analiz_dizini = next((p for p in _adaylar if (p / "main.py").exists()), None)

    # ---- Çıktı dosyalarından KOMPAKT snapshot üret (kalıcı kaydedilecek) ----
    def _sheet(xlsx_path, name, cols=None, limit=None):
        try:
            s = _pd.read_excel(xlsx_path, sheet_name=name)
            if cols:
                s = s[[c for c in cols if c in s.columns]]
            if limit:
                s = s.head(limit)
            return _json.loads(s.to_json(orient="records"))   # NaN -> null
        except Exception:
            return []

    def _snapshot_uret(cikti_dizini, period, demo, rejim_label="Tüm veri", rejim_deger="all"):
        df = _pd.read_csv(cikti_dizini / "trades.csv")
        xlsx = cikti_dizini / "analysis.xlsx"
        # 🔴 KRİTİK DÜZELTME: trades.csv, analiz aracında HER ZAMAN tüm işlemleri
        # (kod_rejimi kolonuyla) içerir. Seçilen rejim burada uygulanmazsa headline
        # (N/PnL/kazanan) TÜM veriyi gösterir → "Güncel" seçili ama 77 işlem/-26.77.
        # Headline'ı da rejime göre süzüyoruz ki whatif/tp_sweep (araçta zaten süzülü)
        # ile TUTARLI olsun ve etiket gerçekten hesaplanan veriyi yansıtsın.
        if rejim_deger and rejim_deger != "all" and "kod_rejimi" in df.columns:
            df = df[df["kod_rejimi"] == rejim_deger].reset_index(drop=True)
        N = int(len(df))
        pnl = _pd.to_numeric(df.get("realizedPnl"), errors="coerce")
        win = int((pnl > 0).sum())
        loss = int((pnl < 0).sum())
        reasons = {}
        if "closeReason" in df.columns:
            reasons = {str(k): int(v) for k, v in df["closeReason"].value_counts().items()}
        whatif = _sheet(xlsx, "whatif",
                        ["tp_mult", "sl_mult", "trades", "timeout_%", "win_rate_%",
                         "expectancy_R", "resolved_expectancy_R", "profit_factor", "reliable"], limit=12)
        return {
            "zaman": _dt.now(_tz.utc).strftime("%d.%m.%Y %H:%M UTC"),
            "period": period, "demo": bool(demo),
            "rejim": rejim_label, "rejim_deger": rejim_deger,   # GÖREV 3: rejim de saklanır
            "N": N, "win": win, "loss": loss, "pnl_sum": round(float(pnl.fillna(0).sum()), 4),
            "close_reasons": reasons,
            "tp_sweep": _sheet(xlsx, "tp_sweep", ["tp_target_R", "hit_rate_%", "expectancy_R"]),
            "whatif": whatif,
            "recommendations": _sheet(xlsx, "recommendations"),
            "distributions": _sheet(xlsx, "distributions"),
            "reliable_any": any(bool(r.get("reliable")) for r in whatif),
        }

    # ---- KOŞTURMA (expander içinde — ana ekranı kalabalıklaştırmasın) ----
    with st.expander("⚙️ Yeni analiz çalıştır / yeniden hesapla",
                     expanded=(len(_analiz_gecmisi_oku()) == 0)):
        if _analiz_dizini is None:
            st.warning("⚠️ `okx_tpsl_analyzer` klasörü bulunamadı. Canlı panelde çalışması için "
                       "klasörün panel deposuna (ai-koalisyon) eklenmiş olması gerekir.")
        else:
            col_s, col_e = st.columns(2)
            _bas = col_s.date_input("Başlangıç", value=None, key="tpsl_bas",
                                    help="Boş = son ~89 gün. OKX yalnızca son 3 ayı verir.")
            _bit = col_e.date_input("Bitiş", value=None, key="tpsl_bit")
            _semboller = st.text_input("Semboller (opsiyonel)", key="tpsl_sym",
                                       placeholder="BTC-USDT-SWAP,ETH-USDT-SWAP — boş = tümü")
            _demo = st.checkbox("Demo modu (API'siz, sentetik veriyle dene)", key="tpsl_demo")

            # GÖREV 1: Kod rejimi seçici. Panelin asıl amacı "ŞU AN kârlı mıyız" olduğu için
            # varsayılan 'Güncel'. (Güncel örneklemi küçükse boş dönebilir; aşağıda nazik uyarı var.)
            _REJIM_SECENEK = {
                "Güncel (tüm düzeltmeler sonrası)": "guncel",
                "Tüm veri (karşılaştırma için)": "all",
                "Kısmi düzeltme sonrası (hacim+MACD)": "kismi_duzeltme",
                "Düzeltme öncesi": "duzeltme_oncesi",
            }
            _rejim_label = st.selectbox(
                "Hangi kod rejimi gösterilsin?",
                list(_REJIM_SECENEK.keys()), index=0, key="tpsl_rejim",
                help="'Güncel' = bugünkü hacim/MACD/BEAT düzeltmeleri yürürlükteyken açılan işlemler "
                     "('şu an kârlı mıyız'). 'Tüm veri' düzeltme öncesi+sonrasını karıştırır (daha büyük "
                     "örneklem ama daha az güncel — kıyaslama için).")
            _rejim_deger = _REJIM_SECENEK[_rejim_label]

            if st.button("▶ Analiz Et (yeniden hesapla)", type="primary"):
                _env = dict(_os.environ)
                try:
                    _env["OKX_API_KEY"] = st.secrets["OKX_API_KEY"]
                    _env["OKX_API_SECRET"] = st.secrets["OKX_SECRET_KEY"]      # ad eşleştirmesi
                    _env["OKX_API_PASSPHRASE"] = st.secrets["OKX_PASSPHRASE"]  # ad eşleştirmesi
                except Exception:
                    if not _demo:
                        st.error("OKX anahtarları panel secrets'ında eksik. Demo modunu deneyin.")
                        st.stop()

                _komut = [_sys.executable, "main.py"]
                _period = ["", ""]
                if _demo:
                    _komut.append("--demo")
                else:
                    if _bas:
                        _komut += ["--start", _bas.strftime("%Y-%m-%d")]; _period[0] = _bas.strftime("%Y-%m-%d")
                    if _bit:
                        _komut += ["--end", _bit.strftime("%Y-%m-%d")]; _period[1] = _bit.strftime("%Y-%m-%d")
                    if _semboller.strip():
                        _komut += ["--symbols", _semboller.strip()]
                # GÖREV 1: seçilen rejimi araca geç (demo dahil).
                _komut += ["--rejim", _rejim_deger]

                with st.spinner("Analiz çalışıyor... (mum verisi çekildiği için 1-3 dakika sürebilir)"):
                    try:
                        _sonuc = _subprocess.run(_komut, cwd=str(_analiz_dizini), env=_env,
                                                 capture_output=True, text=True, timeout=600)
                    except _subprocess.TimeoutExpired:
                        st.error("⏱ Analiz 10 dakikada bitmedi. Daha dar bir tarih aralığı deneyin.")
                        st.stop()

                st.session_state["tpsl_stdout"] = _sonuc.stdout
                st.session_state["tpsl_stderr"] = _sonuc.stderr
                if _sonuc.returncode != 0:
                    _cikti_hepsi = (_sonuc.stderr or "") + (_sonuc.stdout or "")
                    if "işlem yok" in _cikti_hepsi or "rejiminde" in _cikti_hepsi:
                        # Seçilen rejimde hiç işlem yok — hata değil, beklenen durum.
                        st.info(f"ℹ️ Seçtiğiniz rejimde (**{_rejim_label}**) henüz işlem yok. "
                                f"Düzeltmeler çok yeni olduğu için 'Güncel' örneklemi küçük olabilir — "
                                f"**'Tüm veri'** veya **'Kısmi düzeltme sonrası'** seçmeyi deneyin.")
                    else:
                        st.error(f"Analiz hata ile bitti (çıkış kodu {_sonuc.returncode}).")
                        with st.expander("Hata ayrıntısı"):
                            st.code(_sonuc.stderr or "(boş)", language="text")
                else:
                    try:
                        _snap = _snapshot_uret(_analiz_dizini / "output", _period, _demo,
                                               _rejim_label, _rejim_deger)
                        if _analiz_gecmisi_kaydet(_snap):
                            st.session_state["tpsl_taze"] = True   # bu oturumda tam HTML/Excel mevcut
                            st.success("✅ Analiz tamamlandı ve kalıcı olarak kaydedildi.")
                            st.rerun()
                        else:
                            st.warning("Analiz çalıştı ama GitHub'a kaydedilemedi (aşağıda gösteriliyor, kalıcı değil).")
                            st.session_state["tpsl_gecici"] = _snap
                    except Exception as _e:
                        st.error(f"Sonuç özeti çıkarılamadı: {_e}")

    # ================= GÖRÜNTÜLEME (kullanıcı butona basmasa da) =================
    _analizler = _analiz_gecmisi_oku()
    if not _analizler and st.session_state.get("tpsl_gecici"):
        _analizler = [st.session_state["tpsl_gecici"]]   # kaydedilemedi ama gösterelim

    if not _analizler:
        st.info("Henüz kayıtlı analiz yok. Yukarıdaki **⚙️ Yeni analiz çalıştır** bölümünden "
                "ilk analizi başlatın (denemek için 'Demo modu' yeterli).")
        st.stop()

    # Geçmiş analiz seçici (en yeni varsayılan) — etikette rejim de görünsün
    _etiket = lambda i: (f"{_analizler[i]['zaman']} · {_analizler[i].get('rejim', 'Tüm veri')}"
                         + (" · demo" if _analizler[i].get("demo") else ""))
    _sirali = list(reversed(range(len(_analizler))))
    _idx = st.selectbox("Gösterilen analiz", _sirali, format_func=_etiket)
    A = _analizler[_idx]
    N = int(A.get("N", 0))

    # ---- GÖREV 2: EN ÜSTTE HANGİ REJİM / TARİH / ÖRNEKLEM gösteriliyor ----
    _rejim_gos = A.get("rejim", "Tüm veri")
    _per = A.get("period", ["", ""])
    _tarih_gos = ""
    if isinstance(_per, (list, tuple)) and (len(_per) == 2) and (_per[0] or _per[1]):
        _tarih_gos = f" · {_per[0] or '…'} → {_per[1] or 'şimdi'}"
    st.markdown(
        f"<div style='background:#EEF0FF;border:1px solid #7F77DD;border-radius:10px;"
        f"padding:10px 16px;margin-bottom:10px;'>"
        f"<span style='font-size:16px;font-weight:700;color:#3A2FA0;'>🧭 {_rejim_gos}</span>"
        f"<span style='font-size:14px;color:#333;'> — <b>{N} işlem</b>{_tarih_gos}</span></div>",
        unsafe_allow_html=True)

    # ---- KÜÇÜK ÖRNEKLEM UYARISI (göze çarpan banner) ----
    if N < 30:
        st.error(f"⚠️ Bu analiz yalnızca **{N} işleme** dayanıyor. Güvenilir kabul etmeden önce "
                 f"en az **30-50 işlem** birikmesini bekleyin. Aşağıdaki sonuçlar fikir verir, "
                 f"ama istatistiksel olarak kesin değildir.")

    # ---- KATMAN 1: TEK ÖZET KART ----
    _pnl = float(A.get("pnl_sum", 0.0))
    _win, _loss = int(A.get("win", 0)), int(A.get("loss", 0))
    if N < 30:
        _bg, _bd, _ikon, _durum = "#FCF3E1", "#E0A800", "🟡", "belirsiz (veri az)"
    elif _pnl > 0:
        _bg, _bd, _ikon, _durum = "#E1F5EE", "#1D9E75", "🟢", "KÂRDA"
    else:
        _bg, _bd, _ikon, _durum = "#FCEBEB", "#E24B4A", "🔴", "ZARARDA"
    _cumle = (f"Son <b>{N} işlemde</b> mevcut TP/SL ayarınız ortalama <b>{_durum}</b> "
              f"(toplam {_pnl:+.2f} USDT · {_win} kazanan / {_loss} kaybeden). "
              + ("⚠️ Veri az (30'un altında), kesin sonuç sayılmaz."
                 if N < 30 else "Veri miktarı bir fikir vermeye yeterli."))
    st.markdown(
        f"<div style='background:{_bg};border-left:5px solid {_bd};border-radius:10px;"
        f"padding:14px 18px;margin:6px 0 14px;'>"
        f"<div style='font-size:13px;color:#333;line-height:1.5;'>{_ikon} {_cumle}</div></div>",
        unsafe_allow_html=True)

    # ---- KATMAN 2: 3-4 BASİT GÖRSEL ----
    st.markdown("### 📊 Özet Görseller")
    _g1, _g2 = st.columns(2)
    with _g1:
        st.caption("Kazanan / Kaybeden işlem sayısı")
        st.bar_chart(_pd.DataFrame({"İşlem": [_win, _loss]}, index=["Kazanan", "Kaybeden"]),
                     color="#7F77DD")
    with _g2:
        st.caption("Kapanış nedeni")
        _cr = A.get("close_reasons", {})
        if _cr:
            _ceviri = {"TP_HIT": "Kâr al (TP)", "SL_HIT": "Zarar durdur (SL)", "MANUAL": "Manuel",
                       "LIQUIDATION": "Likidasyon", "ADL": "ADL", "UNKNOWN": "Bilinmiyor"}
            st.bar_chart(_pd.DataFrame({"Adet": list(_cr.values())},
                                       index=[_ceviri.get(k, k) for k in _cr]), color="#534AB7")
        else:
            st.caption("Veri yok.")

    _ts = A.get("tp_sweep", [])
    if _ts:
        st.caption("İsabet oranı (hit rate), TP hedefi uzadıkça nasıl düşüyor — "
                   "hedef ne kadar uzaksa fiyat oraya o kadar seyrek ulaşır")
        _tsdf = _pd.DataFrame(_ts)
        if "tp_target_R" in _tsdf and "hit_rate_%" in _tsdf:
            st.line_chart(_tsdf.set_index("tp_target_R")["hit_rate_%"])

    _wf = A.get("whatif", [])
    if _wf:
        _wdf = _pd.DataFrame(_wf)
        try:
            _cur = _wdf[(_wdf["tp_mult"] == 1.0) & (_wdf["sl_mult"] == 1.0)]
            _rel = _wdf[_wdf["reliable"] == True]
            _pool = _rel if not _rel.empty else _wdf
            _best = _pool.loc[_pool["expectancy_R"].idxmax()]
            st.caption("Mevcut ayar vs en iyi alternatif — “1 birim risk başına ortalama "
                       "kazanç” (expectancy) ne kadar yüksekse o kadar iyi")
            _m1, _m2 = st.columns(2)
            _cur_e = float(_cur["expectancy_R"].iloc[0]) if not _cur.empty else float("nan")
            _m1.metric("Mevcut ayarınız", f"{_cur_e:+.2f}" if _cur_e == _cur_e else "—",
                       help="1 birim risk başına ortalama kazanç (expectancy_R)")
            _m2.metric(f"Öneri: TP ×{_best['tp_mult']} / SL ×{_best['sl_mult']}",
                       f"{float(_best['expectancy_R']):+.2f}",
                       delta=(f"{float(_best['expectancy_R']) - _cur_e:+.2f}" if _cur_e == _cur_e else None),
                       help="Alternatif TP/SL çarpanlarının geçmişte verdiği ortalama sonuç")
            if not bool(_best.get("reliable", False)):
                st.caption("⚠️ En iyi senaryo bile 'yetersiz veri' rozetli — kesin öneri sayılmaz.")
        except Exception:
            pass

    # ---- KATMAN 3: KATLANABİLİR TEKNİK DETAYLAR (varsayılan kapalı) ----
    with st.expander("🔧 Teknik Detaylar (ham tablolar)"):
        st.markdown("**Alternatif TP/SL senaryoları** (whatif)")
        st.caption("tp_mult/sl_mult: mevcut TP/SL'nin kaç katı · expectancy_R: 1 birim risk başına "
                   "ort. kazanç · reliable: yeterli veri var mı")
        if A.get("whatif"): st.dataframe(_pd.DataFrame(A["whatif"]), use_container_width=True)
        st.markdown("**TP hedefi taraması** (tp_sweep)")
        if A.get("tp_sweep"): st.dataframe(_pd.DataFrame(A["tp_sweep"]), use_container_width=True)
        st.markdown("**Öneriler** (recommendations)")
        if A.get("recommendations"): st.dataframe(_pd.DataFrame(A["recommendations"]), use_container_width=True)
        st.markdown("**Dağılımlar** (distributions)")
        if A.get("distributions"): st.dataframe(_pd.DataFrame(A["distributions"]), use_container_width=True)

        # Tam HTML rapor + Excel yalnızca YENİ çalıştırılan oturumda mevcut (dosyalar ephemeral)
        if st.session_state.get("tpsl_taze") and _analiz_dizini:
            _rapor = _analiz_dizini / "output" / "report.html"
            _xlsx = _analiz_dizini / "output" / "analysis.xlsx"
            if _rapor.exists():
                st.markdown("**Tam grafikli HTML rapor (bu oturum):**")
                try:
                    _components.html(_rapor.read_text(encoding="utf-8"), height=600, scrolling=True)
                except Exception:
                    pass
            if _xlsx.exists():
                st.download_button("⬇️ Excel raporu (7 sayfa)", _xlsx.read_bytes(),
                                   file_name="tpsl_analysis.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.caption("ℹ️ Tam grafikli HTML rapor ve Excel indirmesi, yalnızca yukarıdan yeni bir "
                       "analiz çalıştırdığınız oturumda görünür (bu dosyalar kalıcı saklanmaz).")
        if st.session_state.get("tpsl_stdout"):
            st.markdown("**Konsol çıktısı**")
            st.code(st.session_state["tpsl_stdout"], language="text")

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
