# OKX TP/SL Excursion Analyzer

OKX Futures (perpetual swap + delivery futures) hesabındaki kapanmış pozisyonları çekip,
girilen **TP/SL seviyelerinin isabetini** MFE/MAE (Maximum Favorable / Adverse Excursion)
bazında geriye dönük ölçen ve maksimum expectancy için seviye önerisi üreten araç.

---

## ⚠️ Önce bilinmesi gereken: OKX 3 ay sınırı

OKX API'si **yalnızca son ~3 ayın** pozisyon ve algo-emir geçmişini veriyor. Resmî
dokümantasyondaki ifadeler:

- `GET /api/v5/account/positions-history` → *"Retrieve the updated position data for the last 3 months."*
- `GET /api/v5/trade/orders-algo-history` → *"Retrieve a list of all algo orders under the current account in the last 3 months."*

Yani `--start 2025-01-01` verilse bile **2025 verisi API'den gelmez**. Bu bir kod eksiği
değil, borsa tarafındaki bir saklama sınırı. Araç bu durumu tespit edip raporun en üstünde
uyarı olarak gösterir ve elindeki veriyle devam eder.

Daha eski veri için tek yol OKX web arayüzünden CSV export almak
(*Order center → Position history → Download*). Mum verisinde böyle bir sınır yok —
`history-candles` yıllar öncesine kadar gidiyor.

---

## Kurulum

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

`.env` içine **salt-okunur (read-only)** bir API key girin — trade/withdraw yetkisi
olmasın:

```
OKX_API_KEY=...
OKX_API_SECRET=...
OKX_API_PASSPHRASE=...
```

`.env` ve `cache/`, `output/` klasörleri `.gitignore`'da.

---

## Kullanım

```bash
python main.py --start 2026-05-01 --end 2026-07-31
```

Belirli sembollerle:

```bash
python main.py --start 2026-05-01 --end 2026-07-31 --symbols BTC-USDT-SWAP,ETH-USDT-SWAP
```

API key olmadan, sentetik veriyle deneme (raporun neye benzediğini görmek için):

```bash
python main.py --demo
```

| Argüman | Açıklama | Varsayılan |
|---|---|---|
| `--start` / `--end` | `YYYY-MM-DD`, dahil | son 89 gün |
| `--symbols` | virgülle ayrık instId listesi | tümü |
| `--inst-types` | `SWAP,FUTURES,MARGIN` | `SWAP,FUTURES` |
| `--bar` | mum periyodu | `1m` |
| `--max-hours` | extension penceresi üst sınırı | `72` |
| `--demo` | sentetik veri, API key gerekmez | — |
| `-v` | debug log | — |

---

## Çıktılar (`output/`)

| Dosya | İçerik |
|---|---|
| `trades.csv` | İşlem bazlı tam tablo (39 kolon) |
| `analysis.xlsx` | 7 sayfa: trades, excursions, distributions, tp_sweep, whatif, scaled_exits, recommendations |
| `report.html` | Grafikler gömülü, tek dosya özet rapor (light/dark) |

Öne çıkan kolonlar: `closeReason`, `preClose_MAE_%ofSLdistance` (SL mesafesinin yüzde kaçı
kullanılmış), `postClose_extra_R` (TP'den sonra kaç R daha gitmiş), `wouldHaveReversed` +
`timeToReversal_h` (SL'den sonra fiyat TP'ye dönmüş mü), `extensionStopReason`.

---

## Metodoloji

### Kapanış nedeni sınıflandırması

Kanıt gücüne göre sırayla:

1. **`positions-history.type`** → 3/4 = likidasyon, 5/6 = ADL. Borsanın kendi beyanı, her
   şeyin üstünde.
2. **`orders-algo-history.actualSide`** (`tp` / `sl`). OKX hangi bacağın tetiklendiğini
   doğrudan söylüyor — bu yüzden kapanış fiyatından geri mühendislik yapmaya gerek yok.
   Orijinal planda fiyat toleransı birincil yöntemdi; dokümantasyon incelemesinde bu alan
   bulununca birincil kanıt o oldu.
3. **Fiyat yakınlığı**: `closeAvgPx`, bilinen TP/SL trigger fiyatına tolerans içinde mi
   (tick ve yüzde toleransının büyüğü). Algo kaydı 3 ay sınırına takıldığında devreye girer.
4. Hiçbiri tutmuyorsa **MANUAL**.

MANUAL / LIQUIDATION / ADL işlemleri ayrı raporlanır ve **TP/SL optimizasyonuna dahil
edilmez**.

### Extension window (adaptif)

TP/SL tetiklendikten sonra:

- En az **4 saat** izlenir.
- Fiyat lehte yeni zirveler yaptıkça pencere uzar.
- Çalışan zirveden **1.5 × ATR** kadar geri çekilme olursa durur (`retrace`).
- Üst sınır **72 saat** (`max_window`), veri biterse `data_end`.

Geri çekilme eşiği neden ATR? Sabit yüzde, BTC ile düşük hacimli bir altcoin'de aynı
anlama gelmiyor; ATR eşiği her enstrümanın kendi volatilitesine göre ölçekleniyor. ATR
hesaplanamazsa %1.5'e düşülür. Eşik mum **kapanışı** üzerinden ölçülür — tek bir fitilin
pencereyi erken kapatmaması için (`EXT_RETRACE_BASIS=extreme` ile değiştirilebilir).

### R tanımı

**1R = giriş–stop mesafesi** (`|entry - sl|`). Tüm `*_R` değerleri risk-normalize, yani
semboller arası karşılaştırılabilir. SL kaydı olmayan işlemlerde R değerleri uydurulmuş bir
paydaya düşmek yerine **NaN** kalır.

### What-if backtest ve iki tuzak

**1. Bar içi belirsizlik.** Tek bir 1 dakikalık mumun aralığı hem alternatif TP'yi hem
alternatif SL'i kapsıyorsa, 1m OHLC hangisinin önce geldiğini söyleyemez. Bu durumda
**stop'un önce dolduğu** varsayılır — yani sonuç işlemin aleyhine çözülür. Sonuçlar bu
nedenle bir **taban değer**; `ambiguous_bars` kolonu bu tie-break'in kaç kez uygulandığını
gösterir.

**2. Çözülmeyen işlemler (timeout).** TP'yi genişlettikçe işlemlerin çoğu mevcut mum
penceresi içinde hiçbir seviyeye ulaşmaz; bunlar pencerenin son kapanışına mark edilir.
Geliştirme sırasında ölçüldü: TP ×2.0 senaryosunda toplam 53.5R'nin **43.4R'si (%81)**
sadece bu mark-to-market'ten geliyordu — yani tablo, exit kuralını değil piyasanın
sürüklenmesini ölçüyordu. Bunun düzeltilmesi için:

- `timeout_%`, `R_from_timeouts` ve `resolved_expectancy_R` (yalnızca gerçekten bir
  seviyeye ulaşan işlemler) ayrı kolonlar olarak raporlanır,
- %35'ten fazla çözülmemiş işlem içeren senaryolar `reliable = False` işaretlenir ve
  sıralamada güvenilir olanların **altına** düşer,
- hiçbir senaryo güvenilir değilse rapor bunu uyarı olarak basar.

Bu düzeltme olmadan araç sistematik olarak "TP'yi genişlet" tavsiyesi üretiyordu.

---

## Verilen kararlar (prompt'taki [MUĞLAK] maddeler)

| Konu | Karar |
|---|---|
| Extension window | Adaptif, 1.5×ATR geri çekilme eşiği, min 4s / maks 72s |
| Kademeli TP | Kullanılmıyor; yine de `scaled_exit_study` ile "eklenseydi ne olurdu" analizi yapılıyor |
| Hedge mode | Kullanılmıyor; net mode varsayıldı (`direction` alanı baz alınır) |
| Trailing stop | Kullanılmıyor; `move_order_stop` sorgulanmıyor |
| Funding fee | Analiz dışı — sadece fiyat hareketi (`pnl`, `fee`/`fundingFee` hariç) |
| Mum granülaritesi | 1 dakika |
| Kapsam | USDT-margined + coin-margined; `SWAP` + `FUTURES` |

### HTTP: neden `ccxt` değil, `requests`

Bu projenin dayandığı üç uç ya ccxt'nin unified API'sinde yok ya da ihtiyaç duyulan
OKX'e özgü alanları (`actualSide`, `tpTriggerPxType`, `posId`, `closeTotalPos`) kaybediyor.
ccxt ile gidilse zaten `implicit` passthrough'a düşülecekti — soyutlama faydası olmadan
bakım yükü gelecekti.

---

## Doğrulanmış API davranışları

Kod yazılmadan önce resmî dokümantasyondan ve canlı API'den teyit edildi:

- `history-candles` limiti **300** (dokümanda 100 sanılıyordu), sonuçlar **en yeniden eskiye**.
- `after=ts` geriye doğru sayfalar; `before=ts` ise ts'ten *sonraki en güncel* mumları
  döndürür — ts'i takip edenleri değil. Bu yüzden geri doldurma **yalnızca `after`** ile yapılır.
- `history-candles` hem derin geçmişi hem güncel ucu kapsıyor; ayrıca `candles` gerekmiyor.
- Mumun son alanı `confirm`; `0` olan (henüz kapanmamış) mumlar atılır, yoksa high/low kesin değil.
- `orders-algo-history`'de `ordType` zorunlu (`conditional,oco` virgülle birleşebilir) ve
  ayrıca **`state` ya da `algoId`'den biri zorunlu** — bu yüzden state'ler üzerinde döngü kurulur.
- `positions-history` `uTime` ile, `orders-algo-history` **`algoId`** ile sayfalanır.
- `positions-history.cTime` = pozisyonun **açılışı**, `uTime` = kapanışı.

---

## Testler

```bash
python -m pytest tests/ -q
```

59 test. Kapsanan uç durumlar: TP'ye hiç ulaşmayan işlem, tetiklenir tetiklenmez dönen
fiyat, pencere sonunda hâlâ süren trend, veri bitmesi, SL'siz işlem (NaN R), short
simetrisi, tek mumda kapanan işlem, hem TP hem SL'i kapsayan mum, timeout muhasebesi,
`after` ile geri sayfalama, ve hatalı API key'in boş sonuç gibi görünmemesi.

---

## Bilinen sınırlar

- **3 aylık geçmiş** (yukarıda).
- `tpTriggerPxType` / `slTriggerPxType` **`mark`** veya `index` olabilir; bu araç son fiyat
  (`last`) mumlarıyla çalışıyor. Mark price ile last price arasındaki fark, tetiklenme
  anının birkaç tick kaymasına yol açabilir. Kolon raporda tutuluyor.
- "SL olmasaydı fiyat TP'ye ulaşırdı" verisi **tamamen hipotetiktir**: o pencerede
  yaşanacak margin call / likidasyon riskini yok sayar. Rapor bunu bir tavsiye olarak değil,
  yalnızca "SL X kat geniş olsaydı bu spesifik örnekte ne olurdu" bilgisi olarak sunar.
- Kısmi kapanışlar (`type=1`) tek bir pozisyon kaydı olarak ele alınır; ortalama kapanış
  fiyatı kullanılır.
