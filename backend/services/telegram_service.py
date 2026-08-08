"""
Telegram Bot Service — SAARTHI.AI.

Handles:
  - Account linking via unique tokens (user generates in Settings → pastes /start TOKEN in bot)
  - Real-time alerts when risk is High/Critical or anomaly detected
  - Two-way AI chat: any message to the bot routes to SAARTHI.AI's Groq chat engine
  - Long-polling loop runs as a background asyncio task inside FastAPI lifespan

Bot: @darpanAi_bot
"""

import asyncio
import random
import string
from datetime import datetime, timezone
from typing import Optional

import httpx
from groq import AsyncGroq

from backend.config import settings
from backend.db.postgres import get_db

TG_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

_offset: int = 0
# Semaphore: max 3 concurrent Groq/AI calls across all telegram chats
_groq_sem = asyncio.Semaphore(3)
# Per-chat locks: ensures one message processed at a time per chat
_chat_locks: dict[int, asyncio.Lock] = {}


# ── Telegram API helpers ───────────────────────────────────────────────────────

async def _tg_post(client: httpx.AsyncClient, method: str, **kwargs) -> dict:
    try:
        r = await client.post(f"{TG_API}/{method}", json=kwargs, timeout=10)
        data = r.json()
        if not data.get("ok"):
            print(f"[telegram] API {method} error: {data.get('description', data)}")
        return data
    except Exception as e:
        print(f"[telegram] API error ({method}): {e}")
        return {}


async def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    async with httpx.AsyncClient() as client:
        result = await _tg_post(client, "sendMessage",
                                chat_id=chat_id, text=text, parse_mode=parse_mode)
        # Telegram rejected the message (bad Markdown entities) — retry as plain text
        if not result.get("ok") and parse_mode:
            print(f"[telegram] Retrying chat_id={chat_id} without parse_mode")
            await _tg_post(client, "sendMessage", chat_id=chat_id, text=text)


async def send_typing(chat_id: int) -> None:
    async with httpx.AsyncClient() as client:
        await _tg_post(client, "sendChatAction", chat_id=chat_id, action="typing")


# ── Token generation & linking ─────────────────────────────────────────────────

def _make_token() -> str:
    chars = string.ascii_uppercase + string.digits
    return "DRP-" + "".join(random.choices(chars, k=6))


async def generate_link_token(user_id: str) -> str:
    """Generate a new link token for the user, replacing any existing one."""
    token = _make_token()
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO telegram_connections (user_id, link_token, linked, created_at)
            VALUES ($1, $2, FALSE, $3)
            ON CONFLICT (user_id) DO UPDATE
              SET link_token = $2, linked = FALSE, created_at = $3, chat_id = NULL, username = NULL
            """,
            user_id, token, datetime.now(timezone.utc),
        )
    return token


async def link_account(token: str, chat_id: int, username: Optional[str]) -> Optional[str]:
    """
    Link a Telegram chat_id to a SAARTHI.AI user via token.
    Returns the user_id if successful, None otherwise.
    """
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM telegram_connections WHERE link_token=$1 AND linked=FALSE",
            token,
        )
        if not row:
            return None
        user_id = row["user_id"]
        await conn.execute(
            """
            UPDATE telegram_connections
            SET chat_id=$1, username=$2, linked=TRUE, linked_at=$3
            WHERE link_token=$4
            """,
            chat_id, username, datetime.now(timezone.utc), token,
        )
    return user_id


async def get_status(user_id: str) -> dict:
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT chat_id, username, linked, linked_at FROM telegram_connections WHERE user_id=$1",
            user_id,
        )
    if not row:
        return {"linked": False}
    return {
        "linked": bool(row["linked"]),
        "username": row["username"],
        "linked_at": row["linked_at"].isoformat() if row["linked_at"] else None,
    }


async def get_chat_id(user_id: str) -> Optional[int]:
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT chat_id FROM telegram_connections WHERE user_id=$1 AND linked=TRUE",
            user_id,
        )
    return int(row["chat_id"]) if row and row["chat_id"] else None


async def get_user_id_by_chat(chat_id: int) -> Optional[str]:
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM telegram_connections WHERE chat_id=$1 AND linked=TRUE",
            chat_id,
        )
    return row["user_id"] if row else None


async def unlink_account(user_id: str) -> None:
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE telegram_connections SET linked=FALSE, chat_id=NULL WHERE user_id=$1",
            user_id,
        )


# ── Alert formatting & sending ─────────────────────────────────────────────────

def _risk_emoji(category: str) -> str:
    return {"Low": "🟢", "Moderate": "🟡", "High": "🟠", "Critical": "🔴"}.get(category, "⚪")


async def send_health_alert(
    user_id: str,
    risk_score: float,
    category: str,
    top_factors: list,
    anomalies: list,
    recommendations: list,
) -> bool:
    chat_id = await get_chat_id(user_id)
    if not chat_id:
        return False

    def _clean(s: str) -> str:
        return str(s).replace("_", " ")

    emoji = _risk_emoji(category)
    factors_text = "\n".join(f"  • {_clean(f)}" for f in top_factors[:3]) or "  • No factors identified"
    rec_text = "\n".join(f"  {i+1}. {_clean(r.get('action', ''))}" for i, r in enumerate(recommendations[:3])) or "  • See SAARTHI.AI for recommendations"

    anomaly_block = ""
    if anomalies:
        anomaly_lines = "\n".join(f"  ⚠️ {_clean(a.get('metric', '?'))}: {_clean(a.get('message', ''))}" for a in anomalies[:2])
        anomaly_block = f"\n\n🚨 *Anomalies Detected*\n{anomaly_lines}"

    msg = f"""{emoji} *SAARTHI.AI Health Alert*

*Risk Score:* {risk_score:.1f}/100 — *{category}*{anomaly_block}

📊 *Primary Risk Drivers*
{factors_text}

💊 *Top Interventions*
{rec_text}

━━━━━━━━━━━━━━━
💬 Reply here to chat with Saarthi AI
🔗 Open [SAARTHI.AI](http://localhost:3000/simulation) for full analysis"""

    await send_message(chat_id, msg)
    return True


async def send_anomaly_alert(user_id: str, anomalies: list) -> bool:
    chat_id = await get_chat_id(user_id)
    if not chat_id or not anomalies:
        return False

    lines = "\n".join(
        f"  ⚠️ {str(a.get('metric','?')).replace('_',' ')} — {str(a.get('message', '')).replace('_',' ')} (severity: {a.get('severity','')})"
        for a in anomalies[:3]
    )
    msg = f"""🚨 *SAARTHI.AI Anomaly Detected*

Your health metrics show abnormal readings:

{lines}

Open SAARTHI.AI to investigate and run a full causal analysis.
💬 Reply here to ask Saarthi AI about this."""

    await send_message(chat_id, msg)
    return True


# ── Bot message handlers ───────────────────────────────────────────────────────

async def _handle_start(chat_id: int, username: Optional[str], args: str) -> None:
    token = args.strip().upper() if args else ""

    if token.startswith("DRP-"):
        user_id = await link_account(token, chat_id, username)
        if user_id:
            await send_message(chat_id, f"""✅ *Account Linked Successfully!*

Your SAARTHI.AI account (`{user_id}`) is now connected to this Telegram.

You'll receive real-time health alerts when:
  🔴 Risk score is High or Critical
  ⚠️ Anomalies are detected in your vitals
  🎯 New AI recommendations are generated

💬 You can also chat with me anytime — just send a message!

Type /help to see all commands.""")
        else:
            await send_message(chat_id, "❌ *Invalid or expired token.*\n\nGenerate a new one from SAARTHI.AI Settings → Connect Telegram.")
    else:
        await send_message(chat_id, f"""👋 *Welcome to SAARTHI.AI Bot!*

I'm Saarthi, your Smart AI Health Guide assistant.

To link your SAARTHI.AI account:
  1. Open SAARTHI.AI → *Settings*
  2. Click *"Generate Link Code"*
  3. Send: `/start YOUR-CODE` to this bot

Once linked, you'll get real-time health alerts and can chat with me about your health data.

💬 Already linked? Just send me any message!""")


async def _handle_status(chat_id: int, user_id: Optional[str]) -> None:
    if not user_id:
        await send_message(chat_id, "⚠️ Account not linked. Send /start to get started.")
        return

    pool = get_db()
    async with pool.acquire() as conn:
        risk_row = await conn.fetchrow(
            "SELECT risk_score, risk_category, top_risk_factors FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1",
            user_id,
        )

    if not risk_row:
        await send_message(chat_id, "📊 No health data yet. Submit a check-in from SAARTHI.AI first.")
        return

    import json
    score = round(float(risk_row["risk_score"]), 1)
    category = risk_row["risk_category"]
    factors = json.loads(risk_row["top_risk_factors"]) if isinstance(risk_row["top_risk_factors"], str) else (risk_row["top_risk_factors"] or [])
    emoji = _risk_emoji(category)
    # Replace underscores with spaces so Telegram Markdown doesn't break on metric names
    factors_clean = [str(f).replace("_", " ") for f in factors[:3]]
    factors_text = ", ".join(factors_clean) or "none"

    await send_message(chat_id, f"""{emoji} *Current Health Status*

*Risk Score:* {score}/100 — *{category}*
*Primary Drivers:* {factors_text}

Open SAARTHI.AI for full simulation and recommendations.""")


async def _handle_help(chat_id: int) -> None:
    await send_message(chat_id, """📖 *SAARTHI.AI Bot Commands*

/start `TOKEN` — Link your SAARTHI.AI account
/status — View your current risk score
/help — Show this message

💬 *Or just chat!* Send any health question and I'll answer using your real health data.

Examples:
  _"What's driving my risk score?"_
  _"What if my stress drops to 3?"_
  _"Explain my causal chain"_""")


async def _handle_chat(chat_id: int, user_id: str, message: str) -> None:
    import re
    await send_typing(chat_id)

    # Step 1: health context from DB
    try:
        from backend.services.chat_service import _fetch_health_context, _build_system_prompt, _client as _groq_client
        ctx = await asyncio.wait_for(_fetch_health_context(user_id), timeout=6.0)
    except Exception as e:
        print(f"[telegram] ctx fetch failed: {type(e).__name__}: {e}")
        ctx = {}

    # Step 2: build system prompt (skip mem0 entirely — too slow for bot)
    try:
        from backend.services.chat_service import _build_system_prompt, _client as _groq_client
        system_prompt = _build_system_prompt(ctx, [])
    except Exception as e:
        print(f"[telegram] prompt build failed: {e}")
        system_prompt = "You are Saarthi, SAARTHI.AI's Smart AI Health Guide assistant. Answer health questions concisely using the patient's data."
        _groq_client = None  # type: ignore

    # Step 3: Groq call — throttled by global semaphore
    try:
        from backend.services.chat_service import _client as _groq_client
        async with _groq_sem:
            resp = await asyncio.wait_for(
                _groq_client().chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    temperature=0.35,
                    max_tokens=400,
                ),
                timeout=35,
            )
        reply = (resp.choices[0].message.content or "").strip()[:3900]
        # Convert **bold** → *bold* for Telegram Markdown, then strip remaining
        # underscores that would break Telegram's legacy Markdown parser
        reply = re.sub(r'\*\*(.+?)\*\*', r'*\1*', reply, flags=re.DOTALL)
        reply = re.sub(r'(?<!\s)_(?!\s)', r' ', reply)  # replace inline underscores
        await send_message(chat_id, reply or "⚠️ No response generated.")
    except asyncio.TimeoutError:
        await send_message(chat_id, "⏱ Response timed out. Please try again.")
    except Exception as e:
        err_str = str(e)[:200]
        print(f"[telegram] Groq failed: {type(e).__name__}: {e}")
        await send_message(chat_id, f"⚠️ Error: {type(e).__name__}: {err_str}")


async def _process_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    username = msg.get("from", {}).get("username")

    if not text:
        return

    # Look up linked user_id for this chat
    user_id = await get_user_id_by_chat(chat_id)

    if text.startswith("/start"):
        args = text[6:].strip()
        await _handle_start(chat_id, username, args)
    elif text == "/status":
        await _handle_status(chat_id, user_id)
    elif text == "/help":
        await _handle_help(chat_id)
    else:
        # Route to AI chat
        if user_id:
            await _handle_chat(chat_id, user_id, text)
        else:
            await send_message(chat_id, "⚠️ Please link your account first.\n\nSend /start to get started.")


# ── Long-polling loop ──────────────────────────────────────────────────────────

async def _process_update_safe(update: dict) -> None:
    """Process one update under a per-chat lock to prevent concurrent Groq flooding."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    try:
        async with _chat_locks[chat_id]:
            await _process_update(update)
    except Exception as e:
        print(f"[telegram] UNHANDLED in update {update.get('update_id')}: {type(e).__name__}: {e}")
        try:
            await send_message(chat_id, "⚠️ Internal error. Please try again.")
        except Exception:
            pass


async def start_bot_polling() -> None:
    """
    Background task: long-polls Telegram for updates and dispatches handlers.
    Runs forever inside FastAPI lifespan.
    """
    if not settings.telegram_bot_token:
        print("[telegram] No bot token configured — polling disabled.")
        return

    global _offset
    print("[telegram] Bot polling started — SAARTHI.AI Bot (@darpanAi_bot)")

    async with httpx.AsyncClient(timeout=40) as client:
        # On startup: fetch any pending messages immediately (timeout=0 = no long-poll)
        # and PROCESS them rather than skip them, so messages sent during restarts aren't lost.
        try:
            resp = await client.get(
                f"{TG_API}/getUpdates",
                params={"offset": _offset, "timeout": 0, "allowed_updates": ["message"]},
            )
            data = resp.json()
            pending = data.get("result", [])
            if pending:
                print(f"[telegram] Processing {len(pending)} pending message(s) from restart...")
                for update in pending:
                    _offset = update["update_id"] + 1
                    asyncio.create_task(_process_update_safe(update))
        except Exception as e:
            print(f"[telegram] Startup drain failed (non-fatal): {e}")


        while True:
            try:
                resp = await client.get(
                    f"{TG_API}/getUpdates",
                    params={"offset": _offset, "timeout": 30, "allowed_updates": ["message"]},
                )
                data = resp.json()
                updates = data.get("result", [])
                for update in updates:
                    _offset = update["update_id"] + 1
                    # Per-chat lock prevents flooding Groq with concurrent messages
                    asyncio.create_task(_process_update_safe(update))
            except asyncio.CancelledError:
                print("[telegram] Polling cancelled.")
                return
            except Exception as e:
                print(f"[telegram] Polling error: {e} — retrying in 5s")
                await asyncio.sleep(5)
