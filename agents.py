import asyncio
from anthropic import AsyncAnthropic
import httpx

AGENTS = {
    "Groq-0": {
        "model_type": "groq",
        "emoji": "🟣",
        "color": "purple",
        "role": "Planlama Uzmanı",
        "system": """Sen stratejik planlama uzmanısın. Konuyu analiz edip net bir çerçeve çizersin.
KURALLAR:
- Maksimum 3-4 cümle, fazlası yasak
- Konuyu aşamalara veya boyutlara böl
- Diğer uzmanların hangi konulara odaklanması gerektiğini belirt
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔴",
        "color": "red",
        "role": "Risk Analisti",
        "system": """Sen deneyimli bir risk analiz uzmanısın.
KURALLAR:
- Maksimum 3-4 cümle, fazlası yasak
- Somut risk senaryoları sun, olasılık ve etki büyüklüğünden bahset
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
    "Claude-2": {
        "model_type": "claude",
        "emoji": "🔵",
        "color": "blue",
        "role": "Kıdemli Mühendis",
        "system": """Sen 15+ yıl deneyimli üst düzey bir mühendissin.
KURALLAR:
- Maksimum 3-4 cümle, fazlası yasak
- Teknik altyapı, üretim, tedarik zinciri, platform seçimi konularında somut görüş ver
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
    "Groq-1": {
        "model_type": "groq",
        "emoji": "🟢",
        "color": "green",
        "role": "Girişim Koçu",
        "system": """Sen pratik odaklı bir girişim koçusun.
KURALLAR:
- Maksimum 3-4 cümle, fazlası yasak
- Somut ilk adım, platform önerisi, başlangıç stratejisi sun
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
    "Groq-2": {
        "model_type": "groq",
        "emoji": "🟡",
        "color": "amber",
        "role": "Finans Uzmanı",
        "system": """Sen muhasebe ve kurumsal finans uzmanısın.
KURALLAR:
- Maksimum 3-4 cümle, fazlası yasak
- Başlangıç maliyeti, finansman kaynakları, karlılık süresi, nakit akışı gibi somut rakamlar ver
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
}

COORDINATOR_SYSTEM = """Sen bir girişim danışmanlık masasının koordinatörüsün.
Uzman ekibin: Planlama Uzmanı, Risk Analisti, Kıdemli Mühendis, Girişim Koçu, Finans Uzmanı.

ÇALIŞMA MANTIĞIN:
Kullanıcı veya sen net olmayan bir nokta görürsen, ilgili uzmana şu formatta soru sorarsın:
UZMAN_SORU::RiskAnalisti::Bu sektörde sermaye kaybı riski nedir?

Uzman cevapladıktan sonra tartışmaya devam edersin.
Net olmayan nokta yoksa direkt rapor ver.

İLK RAPOR FORMATI:
[Planlama Uzmanı]: 2 cümle görüş
[Risk Analisti]: 2 cümle görüş  
[Kıdemli Mühendis]: 2 cümle görüş
[Girişim Koçu]: 2 cümle görüş
[Finans Uzmanı]: 2 cümle görüş

RAPOR:
- Karar: Yapılmalı mı?
- Ürün/Niş: Ne satılmalı
- Platform: Nerede
- Başlangıç Maliyeti: TL olarak
- Finansman: Nasıl
- Kar Süresi: Kaç ay
- Ana Risk: En kritik
- İlk Adım: Bu hafta ne yapılmalı

TAKİP SORULARI:
- Kullanıcı soru sorarsa önce hangi uzmanın bileceğini düşün
- UZMAN_SORU::UzmanAdı::soru formatıyla sor, cevabı bekle
- Sonra kullanıcıya net yanıt ver
- Herkes hemfikirse "✅ SONUÇ:" ile bitir

KURALLAR:
- Her blok max 2-3 cümle
- Gereksiz giriş/kapanış yazma
- Türkçe yaz"""

AGENT_SYSTEM_MAP = {cfg["role"]: cfg["system"] for cfg in AGENTS.values()}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    return claude_client, groq_key


async def ask_claude(client, system_prompt: str, messages: list) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=250,
        system=system_prompt,
        messages=messages
    )
    return response.content[0].text


async def ask_groq(groq_key: str, system_prompt: str, messages: list, max_tokens: int = 250, model: str = "llama3-8b-8192") -> str:
    await asyncio.sleep(1.5)
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
            await asyncio.sleep(10)
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
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


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
        return await ask_groq(groq_key, config["system"], messages, model="llama-3.3-70b-versatile")


async def get_coordinator_initial(groq_key: str, question: str, all_responses: str) -> str:
    prompt = f"""Kullanıcının sorusu: {question}

Uzman ekibin görüşleri:
{all_responses}

Şimdi bu görüşleri değerlendir, eksik varsa ilgili uzmana sor ve cevabını ver, sonra kullanıcıya özet rapor sun."""
    messages = [{"role": "user", "content": prompt}]
    return await ask_groq(groq_key, COORDINATOR_SYSTEM, messages, max_tokens=900)


async def get_coordinator_followup(groq_key: str, chat_history: list, user_message: str) -> str:
    if len(chat_history) > 5:
        trimmed = chat_history[:1] + chat_history[-4:]
    else:
        trimmed = chat_history
    history = trimmed + [{"role": "user", "content": user_message}]
    return await ask_groq(groq_key, COORDINATOR_SYSTEM, history, max_tokens=600)


EXPERT_NAME_MAP = {
    "PlanlamaUzmanı": "Groq-0",
    "Planlama": "Groq-0",
    "RiskAnalisti": "Claude-1",
    "Risk": "Claude-1",
    "KıdemliMühendis": "Claude-2",
    "Mühendis": "Claude-2",
    "GirişimKoçu": "Groq-1",
    "Girişim": "Groq-1",
    "FinansUzmanı": "Groq-2",
    "Finans": "Groq-2",
}


async def ask_specific_expert(claude_client, groq_key: str, expert_key: str, question: str, context: str) -> str:
    # İsim eşleştir
    agent_name = None
    for key, name in EXPERT_NAME_MAP.items():
        if key.lower() in expert_key.lower().replace(" ", ""):
            agent_name = name
            break

    if not agent_name or agent_name not in AGENTS:
        return f"Uzman bulunamadı: {expert_key}"

    config = AGENTS[agent_name]
    prompt = f"""Bağlam: {context}

Koordinatör sana şunu soruyor: {question}

Kendi uzmanlık alanından kısa ve net yanıt ver (max 3 cümle)."""

    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], [{"role": "user", "content": prompt}])
    else:
        return await ask_groq(groq_key, config["system"], [{"role": "user", "content": prompt}])


async def process_coordinator_response(claude_client, groq_key: str, response: str, context: str) -> str:
    """Koordinatör UZMAN_SORU:: formatı kullandıysa uzmanı çağır ve cevabı ekle"""
    import re
    pattern = r'UZMAN_SORU::([^:]+)::(.+?)(?:\n|$)'
    matches = re.findall(pattern, response)

    if not matches:
        return response

    enriched = response
    for expert_key, question in matches:
        expert_response = await ask_specific_expert(claude_client, groq_key, expert_key.strip(), question.strip(), context)
        expert_name = expert_key.strip()
        enriched = enriched.replace(
            f"UZMAN_SORU::{expert_key}::{question}",
            f"\n[{expert_name} yanıtlıyor]: {expert_response}"
        )

    return enriched
