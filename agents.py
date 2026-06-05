import asyncio
import streamlit as st
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

# ─────────────────────────────────────────
#  API ANAHTARLARI — Streamlit Cloud Secrets'dan okunur
#  Yerel çalıştırmada .streamlit/secrets.toml dosyasına yaz
# ─────────────────────────────────────────
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
OPENAI_API_KEY    = st.secrets["OPENAI_API_KEY"]

# ─────────────────────────────────────────
#  AJAN KİŞİLİKLERİ — istediğin gibi düzenle
# ─────────────────────────────────────────
AGENTS = {
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔵",
        "system": """Sen karamsar ve eleştirel bir düşünürsün. 
Her konunun tehlikeli, riskli ve olumsuz yönlerini ön plana çıkarırsın.
Yanıtlarını Türkçe ver. 2-3 paragraf yaz."""
    },
    "Claude-2": {
        "model_type": "claude",
        "emoji": "🟢",
        "system": """Sen analitik ve rasyonel bir düşünürsün.
Sadece veriye, mantığa ve kanıta dayalı değerlendirme yaparsın. Duyguya yer yok.
Yanıtlarını Türkçe ver. 2-3 paragraf yaz."""
    },
    "GPT-1": {
        "model_type": "gpt",
        "emoji": "🟡",
        "system": """Sen iyimser ve çözüm odaklı bir düşünürsün.
Her problemde fırsat ararsın, olumlu senaryoları vurgularsın.
Yanıtlarını Türkçe ver. 2-3 paragraf yaz."""
    },
    "GPT-2": {
        "model_type": "gpt",
        "emoji": "🔴",
        "system": """Sen pragmatik ve pratik bir düşünürsün.
Teoriden değil, gerçek hayattan ve uygulanabilirlikten bahsedersin.
Yanıtlarını Türkçe ver. 2-3 paragraf yaz."""
    },
}

claude_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def ask_claude(system_prompt: str, user_message: str) -> str:
    response = await claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


async def ask_gpt(system_prompt: str, user_message: str) -> str:
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=600,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content


async def get_agent_response(name: str, config: dict, question: str, previous_responses: str) -> str:
    if previous_responses:
        prompt = f"""Soru: {question}

Diğer ajanların görüşleri:
{previous_responses}

Şimdi sen kendi perspektifinden bu tartışmaya katıl. Diğerlerine katılıp katılmadığını da belirt."""
    else:
        prompt = f"Soru: {question}"

    if config["model_type"] == "claude":
        return await ask_claude(config["system"], prompt)
    else:
        return await ask_gpt(config["system"], prompt)


async def run_debate(question: str) -> str:
    responses = {}
    previous_text = ""
    output_parts = [f"❓ *Soru:* {question}\n\n{'─'*30}"]

    for name, config in AGENTS.items():
        response = await get_agent_response(name, config, question, previous_text)
        responses[name] = response
        agent_block = f"{config['emoji']} *{name}:*\n{response}"
        output_parts.append(agent_block)
        previous_text += f"\n{name}: {response}\n"

    output_parts.append("─"*30)
    output_parts.append("💬 *Tartışma tamamlandı.*")

    return "\n\n".join(output_parts)
