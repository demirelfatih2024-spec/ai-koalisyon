import asyncio
from anthropic import AsyncAnthropic
import httpx

# Sıralama önemli — Planlama Uzmanı ilk konuşur, diğerleri ona göre katkı sunar
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
- Planlama uzmanının çerçevesindeki teknik boyutu ele al
- Mimari, sistem tasarımı, teknik altyapı konularında somut görüş ver
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
- Planlama uzmanının çerçevesine göre somut ilk adımı öner
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
- Planlama uzmanının çerçevesindeki finansal boyutu ele al
- Nakit akışı, karlılık, geri dönüş süresi gibi somut metrikler ver
- Gereksiz giriş ve kapanış cümlesi yazma
- Türkçe yaz"""
    },
}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    return claude_client, groq_key


async def ask_claude(client, system_prompt: str, user_message: str) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


async def ask_groq(groq_key: str, system_prompt: str, user_message: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 200,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def get_agent_response(claude_client, groq_key, name: str, config: dict, question: str, previous_responses: str) -> str:
    if not previous_responses:
        # İlk konuşan: Planlama Uzmanı — sadece konuyu çerçevele
        prompt = f"Konu: {question}\n\nBu konuyu analiz et ve diğer uzmanlara çerçeve çiz."
    else:
        # Diğerleri: Planlama uzmanının çerçevesine göre kendi uzmanlık alanından katkı sun
        prompt = f"""Konu: {question}

Ekibin şimdiye kadar söyledikleri:
{previous_responses}

Kendi uzmanlık alanından bu konuya katkı sun. Tekrar etme, tamamla."""

    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], prompt)
    else:
        return await ask_groq(groq_key, config["system"], prompt)
