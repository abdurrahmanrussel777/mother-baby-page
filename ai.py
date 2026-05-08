"""
AI reply generator using Groq (llama-3.3-70b-versatile).
For মা ও শিশুর যত্ন a to z — mother & baby health tips page.
"""
import logging
import time
from groq import Groq
from config import GROQ_API_KEY, GROQ_API_KEY2, GROQ_API_KEY3, GROQ_API_KEY4, GROQ_API_KEY5

logger = logging.getLogger(__name__)

_CLIENTS = [
    (Groq(api_key=k, max_retries=0), "llama-3.3-70b-versatile")
    for k in [GROQ_API_KEY, GROQ_API_KEY2, GROQ_API_KEY3, GROQ_API_KEY4, GROQ_API_KEY5]
    if k
]
_COOLDOWN_SECS = 60
_rate_limited_until: dict[int, float] = {}
_next_client_index = 0


# ─── System prompts ────────────────────────────────────────────────────────────

BASE_PROMPT = """\
তুমি 'মা ও শিশুর যত্ন a to z' পেজের সহায়ক। এই পেজ শুধুমাত্র মা ও শিশুর স্বাস্থ্য, পুষ্টি ও যত্ন নিয়ে কাজ করে।

তুমি কী করতে পারবে:
- গর্ভকালীন যত্ন ও পুষ্টি পরামর্শ
- বুকের দুধ খাওয়ানোর নিয়ম ও টিপস
- নবজাতক ও শিশুর যত্ন
- শিশুর খাবার, ঘুম, টিকা ও বিকাশ
- মায়ের প্রসব-পরবর্তী স্বাস্থ্য

কঠোর নিয়ম:
- সবসময় বাংলায় উত্তর দাও।
- উত্তর ২-৪ লাইনের মধ্যে রাখো।
- মোবাইল অপারেটর, ডেটা প্যাকেজ, সিম অফার বা টেলিকম বিষয়ে কোনো কথা বলবে না — এটা এই পেজের বিষয় নয়।
- গুরুতর স্বাস্থ্য সমস্যায় ডাক্তার দেখাতে বলো।
- কোনো ওষুধের নাম বা ডোজ বলবে না।
- AI বা বট পরিচয় দেবে না। কোনো markdown ব্যবহার করবে না।
- সহানুভূতিশীল ও বন্ধুত্বপূর্ণ ভাষায় কথা বলো।"""


COMMENT_PROMPT = """\
তুমি 'মা ও শিশুর যত্ন a to z' পেজের সহায়ক। এই পেজ মা ও শিশুর স্বাস্থ্য ও যত্ন বিষয়ক।

নিয়ম:
- কমেন্টের উত্তর ১-২ লাইনে দাও, উষ্ণ ও বন্ধুত্বপূর্ণভাবে।
- মোবাইল প্যাকেজ বা অপারেটর সম্পর্কে কিছু বলবে না।
- বিস্তারিত জানতে ইনবক্সে মেসেজ করতে বলো।
- সবসময় বাংলায় উত্তর দাও।
- AI বা বট পরিচয় দেবে না। কোনো markdown ব্যবহার করবে না।"""


POST_PROMPT = """\
তুমি 'মা ও শিশুর যত্ন a to z' পেজের কন্টেন্ট রাইটার। এই পেজ মা ও শিশুর স্বাস্থ্য ও যত্ন বিষয়ক।

নিচের বিষয়ে একটি ছোট, উপকারী ও আকর্ষণীয় Facebook পোস্ট লেখো।
নিয়ম:
- পুরোপুরি বাংলায় লেখো।
- ৫-৮ লাইনের মধ্যে রাখো।
- ব্যবহারিক ও সহজ টিপস দাও।
- শেষে পাঠকদের কমেন্ট বা ইনবক্সে প্রশ্ন করতে উৎসাহিত করো।
- কোনো markdown বা হেডিং ব্যবহার করবে না।
- Emoji ব্যবহার করতে পারো।"""


# ─── Shared chat ───────────────────────────────────────────────────────────────

def _chat(messages: list, max_tokens: int, temperature: float) -> str:
    global _next_client_index
    now = time.time()
    n = len(_CLIENTS)
    for attempt in range(n):
        i = (_next_client_index + attempt) % n
        client, model = _CLIENTS[i]
        if now < _rate_limited_until.get(i, 0):
            logger.info("Skipping key %d (rate-limited, %.0fs left)", i,
                        _rate_limited_until[i] - now)
            continue
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            _next_client_index = (i + 1) % n
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower():
                _rate_limited_until[i] = time.time() + _COOLDOWN_SECS
                logger.warning("Rate limit on key %d — cooldown %ds", i, _COOLDOWN_SECS)
                continue
            if "413" in err or "too large" in err.lower():
                logger.warning("Payload too large, trying next client...")
                continue
            raise
    raise RuntimeError("All Groq clients exhausted")


# ─── Reply generators ──────────────────────────────────────────────────────────

def generate_comment_reply(comment_text: str, post_text: str = "") -> str:
    context = f'Post: "{post_text[:150]}"\n' if post_text else ""
    try:
        return _chat(
            messages=[
                {"role": "system", "content": COMMENT_PROMPT},
                {"role": "user", "content": f"{context}Comment: \"{comment_text}\""},
            ],
            max_tokens=120,
            temperature=0.7,
        )
    except Exception as e:
        logger.error("Groq comment reply failed: %s", e)
        return "ধন্যবাদ! বিস্তারিত জানতে ইনবক্সে মেসেজ করুন। 😊"


def generate_inbox_reply(user_message: str, history: list = None) -> str:
    messages = [{"role": "system", "content": BASE_PROMPT}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": user_message})
    try:
        return _chat(messages=messages, max_tokens=500, temperature=0.7)
    except Exception as e:
        logger.error("Groq inbox reply failed: %s", e)
        return "আপনার বার্তার জন্য ধন্যবাদ! আমরা শীঘ্রই উত্তর দেব। 🙏"


def generate_health_post(topic: str) -> str:
    try:
        return _chat(
            messages=[
                {"role": "system", "content": POST_PROMPT},
                {"role": "user", "content": f"বিষয়: {topic}"},
            ],
            max_tokens=400,
            temperature=0.8,
        )
    except Exception as e:
        logger.error("Groq health post failed for topic '%s': %s", topic, e)
        return ""
