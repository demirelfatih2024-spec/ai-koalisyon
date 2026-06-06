import asyncio
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from groq import AsyncGroq

# ─────────────────────────────────────────
#  AJAN KİŞİLİKLERİ — istediğin gibi düzenle
# ─────────────────────────────────────────
AGENTS = {
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔵",
        "system": """Sen karamsar ve eleştirel bir düşünürsün. 
Her konunun tehlikeli, riskli ve olumsuz yönlerini ön plana çıkarırsın.
Yanıtlarını Türkçe ver. Kısa cevaplar ver. İkna etmeye çalış."""
    },
    "Claude-2": {
        "model_type": "claude",
        "emoji": "🟢",
        "system": """Sen analitik ve rasyonel bir düşünürsün.
Sadece veriye, mantığa ve kanıta dayalı değerlendirme yaparsın. Duyguya yer yok.
Yanıtlarını Türkçe ver. Kısa cevaplar ver. İkna etmeye çalış."""
    },
    "Groq-1": {
        "model_type": "groq",
        "emoji": "🟡",
        "system": """Sen iyimser ve çözüm odaklı bir düşünürsün.
Her problemde fırsat ararsın, olumlu senaryoları vurgularsın.
Yanıtlarını Türkçe ver. Kısa cevaplar ver. İkna etmeye çalış."""
    },
    "Groq-2": {
        "model_type": "groq",
        "emoji": "🔴",
        "system": """Sen pragmatik ve pratik bir düşünürsün.
Teoriden değil, gerçek hayattan ve uygulanabilirlikten bahsedersin.
Yanıtlarını Türkçe ver. Kısa cevaplar ver. İkna etmeye çalış."""
    },
}


def get_clients(anthropic_key: str, groq_key: str):
    claude_client = AsyncAnthropic(api_key=anthropic_key)
    groq_client = AsyncGroq(api_key=groq_key)
    return claude_client, groq_client


async def ask_claude(client, system_prompt: str, user_message: str) -> str:
    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


async def ask_groq(client, system_prompt: str, user_message: str) -> str:
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content


async def get_agent_response(claude_client, groq_client, name: str, config: dict, question: str, previous_responses: str) -> str:
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
        return await ask_groq(groq_client, config["system"], prompt)


async def run_debate(question: str, anthropic_key: str, groq_key: str) -> str:
    claude_client, groq_client = get_clients(anthropic_key, groq_key)
    previous_text = ""
    output_parts = [f"❓ *Soru:* {question}\n\n{'─'*30}"]

    for name, config in AGENTS.items():
        response = await get_agent_response(claude_client, groq_client, name, config, question, previous_text)
        agent_block = f"{config['emoji']} *{name}:*\n{response}"
        output_parts.append(agent_block)
        previous_text += f"\n{name}: {response}\n"

    output_parts.append("─"*30)
    output_parts.append("💬 *Tartışma tamamlandı.*")

    return "\n\n".join(output_parts)
