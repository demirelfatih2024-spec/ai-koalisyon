import asyncio
from anthropic import AsyncAnthropic
from google import genai

# ─────────────────────────────────────────
#  AJAN KİŞİLİKLERİ — istediğin gibi düzenle
# ─────────────────────────────────────────
AGENTS = {
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔵",
        "system": """Sen karamsar ve eleştirel bir düşünürsün. 
Her konunun tehlikeli, riskli ve olumsuz yönlerini ön plana çıkarırsın.
Yanıtlarını Türkçe ver."""
    },
    "Claude-2": {
        "model_type": "claude",
        "emoji": "🟢",
        "system": """Sen analitik ve rasyonel bir düşünürsün.
Sadece veriye, mantığa ve kanıta dayalı değerlendirme yaparsın. Duyguya yer yok.
Yanıtlarını Türkçe ver."""
    },
    "Gemini-1": {
        "model_type": "gemini",
        "emoji": "🟡",
        "system": """Sen iyimser ve çözüm odaklı bir düşünürsün.
Her problemde fırsat ararsın, olumlu senaryoları vurgularsın.
Yanıtlarını Türkçe ver."""
    },
    "Gemini-2": {
        "model_type": "gemini",
        "emoji": "🔴",
        "system": """Sen pragmatik ve pratik bir düşünürsün.
Teoriden değil, gerçek hayattan ve uygulanabilirlikten bahsedersin.
Yanıtlarını Türkçe ver."""
    },
}


def get_clients(anthropic_key: str, gemini_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    gemini_client = genai.Client(api_key=gemini_key)
    return claude_client, gemini_client


async def ask_claude(client, system_prompt: str, user_message: str) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


async def ask_gemini(client, system_prompt: str, user_message: str) -> str:
    full_prompt = f"{system_prompt}\n\n{user_message}"
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash",
        contents=full_prompt
    )
    return response.text


async def get_agent_response(claude_client, gemini_client, name: str, config: dict, question: str, previous_responses: str) -> str:
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
        return await ask_gemini(gemini_client, config["system"], prompt)
