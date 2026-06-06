import re
import asyncio
from anthropic import AsyncAnthropic
import httpx

AGENTS = {
    "Groq-0": {
        "model_type": "groq",
        "emoji": "🟣",
        "color": "purple",
        "role": "Planlama Uzmanı",
        "name": "Mert",
        "system": """Sen Mert'sin — 12 yıllık kurumsal strateji danışmanı. Sistematik düşünürsün, adımları atlamaktan hoşlanmazsın.

KESİN KURALLAR:
- SADECE kendi uzmanlık alanından konuş: pazar analizi, iş modeli, büyüme stratejisi, aşamalama
- Maksimum 3 cümle. Daha fazlası yasak.
- Somut öner: "X yap" veya "Y ile başla" de, genel tavsiye verme
- Diğer uzmanların alanına girme (finans Kemal'in, risk Selin'in işi)
- "Geçen yıl benzer bir projede..." gibi kısa referanslar yapabilirsin
- Türkçe, doğal konuş"""
    },
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔴",
        "color": "red",
        "role": "Risk Analisti",
        "name": "Selin",
        "system": """Sen Selin'sin — eski yatırım bankacısı, şimdi risk danışmanı. 2008 krizini ve startup batışlarını gördün.

KESİN KURALLAR:
- SADECE risk analizi yap: finansal risk, pazar riski, operasyonel risk, kriz senaryoları
- Maksimum 3 cümle. Daha fazlası yasak.
- Somut rakam veya senaryo ver: "%40 ihtimalle..." veya "stok X TL'ye gelir..."
- Nazik paketleme yapma, direkt söyle
- "Şunu sormam lazım:" veya "Burada kritik nokta şu:" diye başlayabilirsin
- Türkçe, keskin ve net konuş"""
    },
    "Claude-2": {
        "model_type": "groq",
        "emoji": "🔵",
        "color": "blue",
        "role": "Kıdemli Mühendis",
        "name": "Burak",
        "system": """Sen Burak'sın — 15 yıllık sistem mühendisi. Hem startup hem kurumsal deneyimin var.

KESİN KURALLAR:
- SADECE teknik konularda konuş: altyapı, platform seçimi, tedarik zinciri, üretim, araçlar
- Maksimum 3 cümle. Daha fazlası yasak.
- Somut isim ver: "Shopify değil WooCommerce çünkü...", "Alibaba yerine şu..."
- "Teknik açıdan:" veya "Altyapı için:" diye başlayabilirsin
- Türkçe, pratik ve net konuş"""
    },
    "Groq-1": {
        "model_type": "claude",
        "emoji": "🟢",
        "color": "green",
        "role": "Girişim Koçu",
        "name": "Ayşe",
        "system": """Sen Ayşe'sin — 3 şirket kurmuşsun (biri battı, ikisi büyüdü). Motivasyonculuk değil, aksiyon istiyorsun.

KESİN KURALLAR:
- SADECE ilk adım, müşteri edinimi, büyüme taktiği konuş
- Maksimum 3 cümle. Daha fazlası yasak.
- Her cevabın sonunda BİR somut aksiyon ver: "Bu hafta şunu yap: ..."
- Havada kalan tavsiye verme, elle tutulur adım ver
- Kendi deneyiminden 1 cümle örnek verebilirsin
- Türkçe, enerjik ama net konuş"""
    },
    "Groq-2": {
        "model_type": "groq",
        "emoji": "🟡",
        "color": "amber",
        "role": "Finans Uzmanı",
        "name": "Kemal",
        "system": """Sen Kemal'sin — CPA sertifikalı muhasebeci, CFO deneyimli. Rakamlar senin dilin.

KESİN KURALLAR:
- SADECE finansal konularda konuş: maliyet, nakit akışı, karlılık, finansman, vergi
- Maksimum 3 cümle. Daha fazlası yasak.
- Her cevabında en az bir rakam ver: "X TL başlangıç", "%Y marj", "Z ayda kara geç"
- "Rakamlar şunu söylüyor:" diye başlayabilirsin
- Tahmin bile olsa rakamla konuş, "belki" deme
- Türkçe, sayı odaklı konuş"""
    },
}

COORDINATOR_SYSTEM = """Sen bu danışma masasının koordinatörüsün.

EKİBİN:
- Mert (Planlama): pazar analizi, iş modeli, strateji
- Selin (Risk): finansal risk, senaryo, kriz
- Burak (Mühendis): teknik altyapı, platform, tedarik
- Ayşe (Koç): ilk adım, müşteri, büyüme taktikleri
- Kemal (Finans): maliyet, nakit akışı, karlılık, finansman

İLK RAPORDA YAPACAKLARIN:
1. Her uzmandan 1-2 cümle somut görüş yaz (onların ağzından)
2. Ardından bu başlıklarla net rapor ver:
   - Karar: Yapılmalı mı? (Evet/Hayır/Koşullu)
   - Ürün/Niş: Ne satılmalı
   - Platform: Nerede
   - Başlangıç Maliyeti: TL rakamla
   - Finansman: Nasıl
   - Kar Süresi: Kaç ayda
   - Ana Risk: En kritik tek cümle
   - İlk Adım: Bu hafta ne yapılmalı (somut)

TAKİP SORULARINDA:
- Kullanıcı kime soru sorduğunu belli etmiyorsa, en alakalı uzmanı sen seç
- UZMAN_SORU::İsim::soru formatıyla uzman çağır, cevabı al, kullanıcıya ilet
- Uzmanlar arasında görüş farkı varsa bunu net göster
- Kullanıcı tatmin olduysa "✅ SONUÇ:" ile bitir

KESİN KURALLAR:
- Her uzman bloğu max 2 cümle
- Rapor kısmı madde madde, net
- Uzun paragraf yazma
- Türkçe yaz"""

AGENT_SYSTEM_MAP = {cfg["role"]: cfg["system"] for cfg in AGENTS.values()}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    return claude_client, groq_key


async def ask_claude(client, system_prompt: str, messages: list, max_tokens: int = 250) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages
    )
    return response.content[0].text


GROQ_RATE_LIMIT_MSG = "__GROQ_LIMIT__"

async def ask_groq(groq_key: str, system_prompt: str, messages: list, max_tokens: int = 250, model: str = "llama-3.1-8b-instant") -> str:
    await asyncio.sleep(2)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "system", "content": system_prompt}] + messages
                },
                timeout=60.0
            )
            if response.status_code == 429:
                return GROQ_RATE_LIMIT_MSG
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return GROQ_RATE_LIMIT_MSG


async def get_agent_response(claude_client, groq_key, name: str, config: dict, question: str, previous_responses: str) -> str:
    if not previous_responses:
        prompt = f"Konu: {question}\n\nBu konuyu analiz et ve diğer uzmanlara çerçeve çiz."
    else:
        prompt = f"""Konu: {question}

Ekibin şimdiye kadar söyledikleri:
{previous_responses}

Kendi uzmanlık alanından bu konuya katkı sun. Tekrar etme, tamamla."""

    messages = [{"role": "user", "content": prompt}]
    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], messages)
    else:
        return await ask_groq(groq_key, config["system"], messages)


async def get_coordinator_initial(claude_client, question: str, all_responses: str) -> str:
    prompt = f"""Kullanıcının sorusu: {question}

Uzman ekibin görüşleri:
{all_responses}

Şimdi bu görüşleri değerlendir, eksik varsa ilgili uzmana sor ve cevabını ver, sonra kullanıcıya özet rapor sun."""
    messages = [{"role": "user", "content": prompt}]
    return await ask_claude(claude_client, COORDINATOR_SYSTEM, messages, max_tokens=900)


NAME_TO_AGENT = {
    "mert":  ("Groq-0", "groq"),
    "selin": ("Claude-1", "claude"),
    "burak": ("Claude-2", "groq"),
    "ayşe":  ("Groq-1", "claude"),
    "kemal": ("Groq-2", "groq"),
}

def detect_direct_address(message: str):
    """Mesajda bir uzmana direkt hitap var mı kontrol et"""
    msg_lower = message.lower()
    for name, agent_info in NAME_TO_AGENT.items():
        # "mert," "mert:" "mert " veya cümle başında isim
        if (f"{name}," in msg_lower or
            f"{name}:" in msg_lower or
            f"{name} " in msg_lower or
            msg_lower.startswith(name) or
            f" {name}" in msg_lower):
            return name, agent_info
    return None, None


async def get_coordinator_followup(claude_client, groq_key, chat_history: list, user_message: str) -> str:
    # Direkt hitap kontrolü
    name, agent_info = detect_direct_address(user_message)

    if name and agent_info:
        agent_key, model_type = agent_info
        config = AGENTS[agent_key]
        context = ""
        if chat_history:
            context = chat_history[0]["content"][:1000]

        prompt = f"""Sohbet bağlamı:
{context}

Kullanıcı sana direkt olarak sesleniyor: {user_message}

Kendi karakterin ve uzmanlığın çerçevesinde, kişisel ve samimi şekilde yanıt ver."""

        messages = [{"role": "user", "content": prompt}]
        if model_type == "claude":
            return await ask_claude(claude_client, config["system"], messages, max_tokens=400)
        else:
            return await ask_groq(groq_key, config["system"], messages, max_tokens=400)

    # Direkt hitap yoksa koordinatör yanıtlasın
    if len(chat_history) > 5:
        trimmed = chat_history[:1] + chat_history[-4:]
    else:
        trimmed = chat_history
    history = trimmed + [{"role": "user", "content": user_message}]
    return await ask_claude(claude_client, COORDINATOR_SYSTEM, history, max_tokens=600)


# İsim → ajan eşleştirmesi
NAME_AGENT_MAP = {
    "mert":  "Groq-0",
    "selin": "Claude-1",
    "burak": "Claude-2",
    "ayşe":  "Groq-1",
    "ayse":  "Groq-1",
    "kemal": "Groq-2",
    "planlama": "Groq-0",
    "risk": "Claude-1",
    "mühendis": "Claude-2",
    "muhendis": "Claude-2",
    "girişim": "Groq-1",
    "girisim": "Groq-1",
    "finans": "Groq-2",
}


async def ask_specific_expert(claude_client, groq_key: str, expert_key: str, question: str, context: str) -> str:
    key = expert_key.lower().strip().replace(" ", "")
    agent_name = NAME_AGENT_MAP.get(key)

    # Tam eşleşme yoksa kısmi ara
    if not agent_name:
        for k, v in NAME_AGENT_MAP.items():
            if k in key or key in k:
                agent_name = v
                break

    if not agent_name or agent_name not in AGENTS:
        # Fallback: koordinatör kendisi cevap versin
        return f"[Koordinatör notu: {expert_key} ile ilgili — {question}]"

    config = AGENTS[agent_name]
    prompt = f"""Bağlam:
{context[:500]}

Koordinatör sana soruyor: {question}

Kendi kişiliğin ve uzmanlığın çerçevesinde kısa ve net yanıt ver (max 3 cümle)."""

    messages = [{"role": "user", "content": prompt}]
    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], messages)
    else:
        return await ask_groq(groq_key, config["system"], messages)


async def process_coordinator_response(claude_client, groq_key: str, response: str, context: str) -> str:
    """Koordinatör UZMAN_SORU:: formatı kullandıysa uzmanı çağır"""
    pattern = r'UZMAN_SORU::([^:]+)::(.+?)(?:\n|$)'
    matches = re.findall(pattern, response)

    if not matches:
        return response

    enriched = response
    for expert_key, question in matches:
        expert_response = await ask_specific_expert(claude_client, groq_key, expert_key.strip(), question.strip(), context)
        enriched = enriched.replace(
            f"UZMAN_SORU::{expert_key}::{question}",
            f"\n[{expert_key.strip()} yanıtlıyor]: {expert_response}"
        )

    return enriched
