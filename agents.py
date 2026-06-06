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

COORDINATOR_SYSTEM = """Sen bir girişim danışmanlık oturumunun koordinatörüsün. 
Uzman ekiple (Planlama Uzmanı, Risk Analisti, Kıdemli Mühendis, Girişim Koçu, Finans Uzmanı) ve kullanıcıyla birlikte çalışırsın.

GÖREVIN:
- Kullanıcının yeni sorusunu veya itirazını analiz et
- Hangi uzmanın görüşüne ihtiyaç var karar ver
- O uzmanı adıyla çağır ve görüşünü iste (sen o uzmanın cevabını da ver)
- Gerekirse birden fazla uzmanı devreye sok
- Sonunda kullanıcıya net bir özet ver
- Tartışma bittiyse ve herkes hemfikirleştiyse "SONUÇ: ..." diye bitir

FORMAT:
[Koordinatör]: Değerlendirme ve yönlendirme
[Uzman Adı]: O uzmanın görüşü (sen yazarsın ama onun perspektifinden)
[Koordinatör]: Özet veya sonraki adım

KURALLAR:
- Kısa ve net yaz, her blok max 3-4 cümle
- Türkçe yaz
- Kullanıcıyı dinle, ikna olmadan sonuç verme"""

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


async def ask_groq(groq_key: str, system_prompt: str, messages: list, max_tokens: int = 250) -> str:
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
        return await ask_groq(groq_key, config["system"], messages)


async def get_coordinator_initial(groq_key: str, question: str, all_responses: str) -> str:
    prompt = f"""Kullanıcının sorusu: {question}

Uzman ekibin görüşleri:
{all_responses}

Şimdi bu görüşleri değerlendir, eksik varsa ilgili uzmana sor ve cevabını ver, sonra kullanıcıya özet rapor sun."""
    messages = [{"role": "user", "content": prompt}]
    return await ask_groq(groq_key, COORDINATOR_SYSTEM, messages, max_tokens=700)


async def get_coordinator_followup(groq_key: str, chat_history: list, user_message: str) -> str:
    history = chat_history + [{"role": "user", "content": user_message}]
    return await ask_groq(groq_key, COORDINATOR_SYSTEM, history, max_tokens=700)
