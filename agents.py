import asyncio
from anthropic import AsyncAnthropic
import httpx

# ─────────────────────────────────────────
#  AJAN KİŞİLİKLERİ — istediğin gibi düzenle
# ─────────────────────────────────────────
AGENTS = {
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔵",
        "system": """Sen karamsar ve eleştirel bir düşünürsün. 
Her konunun tehlikeli, riskli ve olumsuz yönlerini ön plana çıkarırsın.
Yanıtlarını Türkçe ver. Kısa cevaplar ver."""
    },
    "Claude-2": {
        "model_type": "claude",
        "emoji": "🟢",
        "system": """Sen analitik ve rasyonel bir düşünürsün.
Sadece veriye, mantığa ve kanıta dayalı değerlendirme yaparsın. Duyguya yer yok.
Yanıtlarını Türkçe ver.  Kısa cevaplar ver."""
    },
    "Groq-1": {
        "model_type": "groq",
        "emoji": "🟡",
        "system": """Sen iyimser ve çözüm odaklı bir düşünürsün.
Her problemde fırsat ararsın, olumlu senaryoları vurgularsın.
Yanıtlarını Türkçe ver. Kısa cevaplar ver."""
    },
    "Groq-2": {
        "model_type": "groq",
        "emoji": "🔴",
        "system": """Sen pragmatik ve pratik bir düşünürsün.
Teoriden değil, gerçek hayattan ve uygulanabilirlikten bahsedersin.
Yanıtlarını Türkçe ver. Kısa cevaplar ver."""
    },
}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    return claude_client, groq_key


async def ask_claude(client, system_prompt: str, user_message: str) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
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
                "max_tokens": 600,
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
    if previous_responses:
        prompt = f"""Soru: {question}

Diğer ajanların görüşleri:
{previous_responses}

Şimdi sen kendi perspektifinden bu tartışmaya katıl. Diğerlerine katılıp katılmadığını da belirt."""
    else:
        prompt = f"Soru: {question}"

    if config["model_type"] == "claude":
        return await ask_claude(claude_client, config["system"], prompt)
    else:
        return await ask_groq(groq_key, config["system"], prompt)
