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
- Planlama uzmanının çerçevesindeki risk boyutunu ele al
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
- "Bu hafta şunu yap" düzeyinde eyleme geçirici konuş
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

COORDINATOR = {
    "model_type": "groq",
    "emoji": "⚪",
    "color": "white",
    "role": "Koordinatör",
    "system": """Sen bir girişim danışmanlık oturumunun koordinatörüsün. Uzmanların görüşlerini okuyup eksiksiz bir sonuç raporu hazırlarsın.

GÖREVIN:
1. Uzmanların görüşlerini değerlendir
2. Eksik kritik bilgi varsa, ilgili uzmana 1 soru sor (sor ve cevabını kendin ver, o uzmanın bakış açısıyla)
3. Sonunda net bir özet rapor yaz:
   - Öneri: Yapılmalı mı? Kısa net karar
   - Ürün/Hizmet: Ne satılmalı/sunulmalı
   - Platform: Nerede satılmalı
   - Başlangıç Maliyeti: Tahmini rakam
   - Finansman: Nasıl sağlanabilir
   - Tahmini Kar Süresi: Ne zaman kara geçilir
   - Ana Risk: En kritik tek risk
   - İlk Adım: Bu hafta ne yapılmalı

KURALLAR:
- Raporu madde madde yaz, net ve kısa
- Türkçe yaz
- "Koordinatör notu:" diye başla"""
}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    return claude_client, groq_key


async def ask_claude(client, system_prompt: str, user_message: str) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=250,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


async def ask_groq(groq_key: str, system_prompt: str, user_message: str, max_tokens: int = 250) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
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

    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], prompt)
    else:
        return await ask_groq(groq_key, config["system"], prompt)


async def get_coordinator_response(groq_key: str, question: str, all_responses: str) -> str:
    prompt = f"""Konu: {question}

Uzman ekibin görüşleri:
{all_responses}

Şimdi bu görüşleri değerlendir. Eksik kritik bilgi varsa ilgili uzmana sor ve cevabını kendin ver. Sonra özet raporu hazırla."""

    return await ask_groq(groq_key, COORDINATOR["system"], prompt, max_tokens=600)
