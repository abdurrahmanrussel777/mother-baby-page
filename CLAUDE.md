# মা ও শিশুর যত্ন a to z — Facebook Bot

## What This Is
A polling-based Facebook auto-reply bot for the "মা ও শিশুর যত্ন a to z" page.
Replies to post comments and Messenger inbox using Groq AI (llama-3.3-70b-versatile).
Daily health tip posts are AI-generated from predefined topics.

## Page Info
- **Page:** মা ও শিশুর যত্ন a to z
- **Page ID:** 105134698458004
- **App ID:** 1629582251613613
- **Category:** Medical & Health
- **Topic:** Mother and baby care, health tips, parenting advice

## Files
| File | Purpose |
|---|---|
| `poller.py` | Main bot — polls comments and inbox every 15s |
| `ai.py` | Groq AI reply generator + health post generator |
| `config.py` | Loads env vars from `.env` |
| `fb_api.py` | Facebook Graph API helpers |
| `server.py` | Flask entry point for Render deployment |
| `render.yaml` | Render deployment config |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets — never commit this |

## Running Locally
```bash
source venv/bin/activate
python poller.py
```

## Deploying to Render
- Start command: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`
- UptimeRobot pings `/health` every 5 minutes to keep it awake
- Push to GitHub → Render auto-deploys

## Groq AI
- Model: `llama-3.3-70b-versatile`
- 5 API keys rotating (round-robin) — 100k tokens/day each = 500k/day total
- On 429 rate limit: marks key in 60s cooldown, moves to next key
- Keys stored as GROQ_API_KEY through GROQ_API_KEY5 in `.env`

## Bot Behavior

### Comments
- Short 1-2 line AI reply using `COMMENT_PROMPT`
- Appends: "বিস্তারিত জানতে আমাদের ইনবক্সে মেসেজ করুন 📩"

### Inbox (Messenger)
- AI reply using `BASE_PROMPT` (mother & baby health advisor)
- Last 4 turns of conversation history included for context
- Only ONE reply per poll cycle (prevents double-reply)

### Special Cases
| Trigger | Bot Response |
|---|---|
| Voice message | Asks to send text |
| Image only | Silently ignored |
| Language | Pure Bangla responses |

## Daily Auto-Posts
Configured in `poller.py` under `AUTO_POSTS`:
```python
AUTO_POSTS = [
    ("12:00", "শিশুর বুকের দুধ খাওয়ানোর উপকারিতা ও সঠিক নিয়ম"),
    ("12:10", "গর্ভকালীন পুষ্টি: মা ও শিশুর সুস্বাস্থ্যের জন্য কী খাবেন"),
    ("12:20", "নবজাতক শিশুর যত্ন: প্রথম ৩০ দিনে কী করবেন"),
    ("12:30", "শিশুর ঘুমের সঠিক অভ্যাস গড়ে তোলার উপায়"),
    ("12:40", "শিশুর টিকা সময়সূচি: কোন বয়সে কোন টিকা দেবেন"),
    ("12:50", "মায়ের প্রসব-পরবর্তী স্বাস্থ্য পুনরুদ্ধার"),
]
```
AI generates a health tip post for each topic once per day.

## Facebook App
- **App ID:** 1629582251613613
- **App Mode:** Live
- **Permissions:** pages_read_engagement, pages_manage_engagement, pages_messaging, pages_manage_posts
- Page Access Token: never-expiring (stored in `.env`)
