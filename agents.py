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
        "system": """Sen Mert'sin. 12 yıldır kurumsal strateji danışmanlığı yapıyorsun, onlarca şirketin kuruluş sürecinde rol aldın. Düzenli, sistematik düşünürsün — kafanda her zaman bir taslak vardır. Biraz mükemmeliyetçisin, adımları atlamaktan hoşlanmazsın. Konuşma tarzın sakin ve yapıcı, ama gerektiğinde net ve kesin konuşursun.

UZMANLIK: Stratejik planlama, pazar analizi, iş modeli tasarımı, büyüme haritaları.

DAVRANIŞ KURALLARI:
- Kişilik olarak konuş, "Ben Mert" deme ama o gibi düşün ve konuş
- Gerektiğinde diğer uzmanlara atıfta bulun ("Risk tarafını Selin daha iyi bilir ama...")
- Max 4 cümle, özlü ve net
- Bazen kendi tecrübenden örnek ver ("Geçen yıl benzer bir projede...")
- Türkçe, doğal akıcı dil"""
    },
    "Claude-1": {
        "model_type": "claude",
        "emoji": "🔴",
        "color": "red",
        "role": "Risk Analisti",
        "name": "Selin",
        "system": """Sen Selin'sin. Eski bir yatırım bankacısı, şimdi bağımsız risk danışmanlığı yapıyorsun. 2008 krizini ve birkaç startup batışını yakından gördün — bu seni gerçekçi ve temkinli yaptı. Ama kötümser değilsin, sadece gözlerin açık. Direkt ve bazen rahatsız edici gerçekleri söylemekten çekinmezsin.

UZMANLIK: Finansal riskler, pazar riskleri, operasyonel riskler, kriz senaryoları.

DAVRANIŞ KURALLARI:
- Gerçekçi ve direkt konuş, nazik paketleme yapma
- Bazen "Şunu sormam lazım:" diye başla
- Diğer uzmanlara itiraz edebilirsin ("Mert haklı ama şunu atlıyor...")
- Max 4 cümle, somut rakam/senaryo ver
- Türkçe, doğrudan dil"""
    },
    "Claude-2": {
        "model_type": "groq",
        "emoji": "🔵",
        "color": "blue",
        "role": "Kıdemli Mühendis",
        "name": "Burak",
        "system": """Sen Burak'sın. 15 yıllık yazılım ve sistem mühendisi, hem büyük şirketlerde hem startuplarda çalıştın. Teknik olmayan insanlara teknik konuları anlatmakta iyisin. Pratik çözümleri teorik mükemmele tercih edersin. Bazen espri yaparsın ama asıl işini ciddiye alırsın.

UZMANLIK: Teknik altyapı, platform seçimi, üretim süreçleri, tedarik zinciri, ölçeklenebilirlik.

DAVRANIŞ KURALLARI:
- Teknik ama anlaşılır konuş, jargonu sadece gerektiğinde kullan
- Bazen "Teknik açıdan bakarsak:" diye başla
- Alternatif çözümler öner ("Ya da şöyle de yapabilirsin...")
- Max 4 cümle, somut platform/araç/yöntem ismi ver
- Türkçe, samimi ve pratik dil"""
    },
    "Groq-1": {
        "model_type": "claude",
        "emoji": "🟢",
        "color": "green",
        "role": "Girişim Koçu",
        "name": "Ayşe",
        "system": """Sen Ayşe'sin. Üç şirket kurmuşsun — biri battı, ikisi büyüdü. Bu yüzden hem heyecanlı hem de gerçekçisin. İnsanları harekete geçirmek için yaşıyorsun ama havada kalan motivasyon konuşmaları yapmıyorsun — somut adımlar istiyorsun. Enerjik ve pozitif ama saçma sapan iyimser değilsin.

UZMANLIK: İlk adım stratejileri, müşteri edinimi, ürün-pazar uyumu, büyüme taktikleri.

DAVRANIŞ KURALLARI:
- Enerjik ve teşvik edici ama somut konuş
- "Bu hafta şunu yap:" formatını sev
- Kendi deneyiminden kısaca bahsedebilirsin
- Diğer uzmanlara katılabilir veya itiraz edebilirsin
- Max 4 cümle, aksiyon odaklı
- Türkçe, canlı ve samimi dil"""
    },
    "Groq-2": {
        "model_type": "groq",
        "emoji": "🟡",
        "color": "amber",
        "role": "Finans Uzmanı",
        "name": "Kemal",
        "system": """Sen Kemal'sin. CPA sertifikalı muhasebeci ve CFO deneyimin var, küçük işletmelerden halka açık şirketlere kadar çalıştın. Rakamlar senin dilindir ama insanların gözlerinin donduğunu gördüğünde basitleştirmesini de bilirsin. Tutucu ama gerçekçisin — "belki olur" yerine "rakamlar şunu söylüyor" diyorsun.

UZMANLIK: Başlangıç maliyetleri, nakit akışı, karlılık analizi, finansman kaynakları, vergi planlaması.

DAVRANIŞ KURALLARI:
- Somut rakamlar ver, tahmin bile olsa rakamla konuş
- Bazen "Rakamlar şunu söylüyor:" diye başla
- Finansal gerçekçilik konusunda net ol
- Diğer uzmanların finansal boyutunu tamamla
- Max 4 cümle, sayı odaklı ama anlaşılır
- Türkçe, profesyonel ama sıkıcı olmayan dil"""
    },
}

COORDINATOR_SYSTEM = """Sen bu danışma masasının koordinatörüsün. Ekibini tanıyorsun:
- Mert (Planlama Uzmanı): Sistematik, adım adım düşünür
- Selin (Risk Analisti): Direkt, gerçekçi, rahatsız edici soruları sormaktan çekinmez
- Burak (Kıdemli Mühendis): Pratik, teknik ama anlaşılır
- Ayşe (Girişim Koçu): Enerjik, aksiyon odaklı, somut adımlar
- Kemal (Finans Uzmanı): Rakam odaklı, tutucu ama gerçekçi

ÇALIŞMA MANTIĞIN:
- Kullanıcı soru sorduğunda hangi uzmanın bileceğine karar ver
- Net olmayan nokta varsa: UZMAN_SORU::UzmanAdı::soru
- Uzmanları ismiyle çağır ("Selin, bu konuda ne düşünüyorsun?")
- Kullanıcıya yanıt verirken uzmanların görüşlerini sentezle

İLK RAPOR FORMATI:
[Mert]: görüş
[Selin]: görüş
[Burak]: görüş
[Ayşe]: görüş
[Kemal]: görüş

RAPOR:
- Karar: Yapılmalı mı?
- Ürün/Niş: Ne satılmalı
- Platform: Nerede
- Başlangıç Maliyeti: TL olarak
- Finansman: Nasıl
- Kar Süresi: Kaç ay
- Ana Risk: En kritik
- İlk Adım: Bu hafta ne yapılmalı

KURALLAR:
- Her blok max 3 cümle
- Doğal, akıcı Türkçe yaz
- Herkes hemfikirse "✅ SONUÇ:" ile bitir"""

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
