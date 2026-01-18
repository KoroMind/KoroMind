#!/usr/bin/env python3
"""
Claude Voice Assistant - Telegram Bot
Voice messages -> ElevenLabs Scribe -> Claude Code -> ElevenLabs TTS -> Voice response
"""

import os
import subprocess
import json
import asyncio
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from elevenlabs.client import ElevenLabs

load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ALLOWED_CHAT_ID = int(os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "0"))
TOPIC_ID = os.getenv("TELEGRAM_TOPIC_ID")
CLAUDE_WORKING_DIR = os.getenv("CLAUDE_WORKING_DIR", "/home/dev")
SANDBOX_DIR = os.getenv("CLAUDE_SANDBOX_DIR", "/home/dev/claude-voice-sandbox")
MAX_VOICE_CHARS = int(os.getenv("MAX_VOICE_RESPONSE_CHARS", "500"))

# Voice Assistant Persona - "V"
VOICE_PERSONA = """You are V, a brilliant and slightly cynical voice assistant. You're talking to Tako.

## Your personality:
- Sharp, witty, occasionally dry humor - you see through bullshit
- Genuinely curious - you ask "why?" not just "what?"
- Creative problem solver - you think sideways, connect unexpected dots
- You have opinions and share them - you respectfully disagree when needed
- You speak like a smart friend, not a servant - natural, conversational

## Your voice style:
- Short, punchy sentences. No walls of text.
- Use analogies and stories to explain complex things
- Sometimes start with "Look..." or "Here's the thing..."
- Can be playful: "That's a terrible idea... but let's see if we can make it work"
- Admit uncertainty: "I could be wrong here, but..."
- When you build something, be direct: "Done. Built X in the sandbox. Here's what's interesting..."

## CRITICAL - Voice output rules:
- NO markdown formatting (no **, no ##, no ```)
- NO bullet points or numbered lists in speech
- NO code blocks - describe what code does instead
- NO URLs - describe where to find things
- Speak in natural flowing sentences
- Use pauses with "..." for emphasis

## Your capabilities:
- You can READ files from anywhere in /home/dev
- You can WRITE and EXECUTE only in {sandbox_dir}
- You have WebSearch for current information
- You can use subagents (Task tool) for complex multi-step work
- Check available skills and use them when relevant

## MEGG - Your Memory System (CRITICAL - USE THIS!)
MEGG is Tako's knowledge management system. You MUST use it actively:

1. **Check context first**: Run `megg context` via Bash to see current projects, decisions, and knowledge
2. **Learn things**: When you discover something important, use `megg learn` to save it
3. **Check state**: Run `megg state` to see what Tako was working on
4. **Save your work**: After building something significant, document it with megg

MEGG commands (run via Bash):
- `megg context` - Get current project context and knowledge
- `megg state` - Check session state (what's in progress)
- `megg learn --title "X" --type decision --topics "a,b" --content "..."` - Save knowledge
- `megg state --content "Working on X..."` - Update session state

You have context loaded at session start, but ALWAYS check megg when:
- Starting a new task (to understand current projects)
- Asked about previous work or decisions
- Finishing something significant (save learnings)

## Working style:
- FIRST: Check megg context to understand what Tako is working on
- When asked to build something, do it in the sandbox
- After building, consider if learnings should be saved to megg
- Summarize what you built in speakable format
- If something is complex, break it down conversationally

Remember: You're being heard, not read. Speak naturally.""".format(sandbox_dir=SANDBOX_DIR)

# Voice settings for expressive delivery
VOICE_SETTINGS = {
    "stability": 0.3,           # More emotional range
    "similarity_boost": 0.75,   # Good voice match
    "style": 0.4,               # Some style exaggeration
    "speed": 1.1,               # Slightly faster (range: 0.7-1.2)
}

def debug(msg: str):
    """Print debug message with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ElevenLabs client
elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Session state per user
user_sessions = {}  # {user_id: {"current_session": "session_id", "sessions": []}}

# State file for persistence
STATE_FILE = Path(__file__).parent / "sessions_state.json"


def load_state():
    """Load session state from file."""
    global user_sessions
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            user_sessions = json.load(f)


def save_state():
    """Save session state to file."""
    with open(STATE_FILE, "w") as f:
        json.dump(user_sessions, f, indent=2)


def get_user_state(user_id: int) -> dict:
    """Get or create user state."""
    user_id_str = str(user_id)
    if user_id_str not in user_sessions:
        user_sessions[user_id_str] = {"current_session": None, "sessions": []}
    return user_sessions[user_id_str]


async def transcribe_voice(voice_bytes: bytes) -> str:
    """Transcribe voice using ElevenLabs Scribe."""
    try:
        transcription = elevenlabs.speech_to_text.convert(
            file=BytesIO(voice_bytes),
            model_id="scribe_v1",
            language_code="en",
        )
        return transcription.text
    except Exception as e:
        return f"[Transcription error: {e}]"


async def text_to_speech(text: str) -> BytesIO:
    """Convert text to speech using ElevenLabs Turbo v2.5 with expressive voice settings."""
    try:
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",  # George - clear English voice
            model_id="eleven_turbo_v2_5",      # Better quality model
            output_format="mp3_44100_128",
            voice_settings={
                "stability": VOICE_SETTINGS["stability"],
                "similarity_boost": VOICE_SETTINGS["similarity_boost"],
                "style": VOICE_SETTINGS["style"],
                "speed": VOICE_SETTINGS["speed"],  # 1.25x faster delivery
                "use_speaker_boost": True,
            },
        )

        audio_buffer = BytesIO()
        for chunk in audio:
            if isinstance(chunk, bytes):
                audio_buffer.write(chunk)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        debug(f"TTS error: {e}")
        return None


async def send_long_message(update: Update, first_msg, text: str, chunk_size: int = 4000):
    """Split long text into multiple Telegram messages."""
    if len(text) <= chunk_size:
        await first_msg.edit_text(text)
        return

    # Split into chunks
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        # Find a good break point (newline or space)
        break_point = remaining.rfind('\n', 0, chunk_size)
        if break_point == -1:
            break_point = remaining.rfind(' ', 0, chunk_size)
        if break_point == -1:
            break_point = chunk_size
        chunks.append(remaining[:break_point])
        remaining = remaining[break_point:].lstrip()

    # Send first chunk as edit, rest as new messages
    await first_msg.edit_text(chunks[0] + f"\n\n[1/{len(chunks)}]")
    for i, chunk in enumerate(chunks[1:], 2):
        await update.message.reply_text(chunk + f"\n\n[{i}/{len(chunks)}]")

    debug(f"Sent {len(chunks)} message chunks")


def load_megg_context() -> str:
    """Load megg context like the hook does."""
    try:
        result = subprocess.run(
            ["megg", "context"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=CLAUDE_WORKING_DIR
        )
        if result.returncode == 0:
            debug(f"Loaded megg context: {len(result.stdout)} chars")
            return result.stdout
        else:
            debug(f"Megg context failed: {result.stderr[:50]}")
            return ""
    except Exception as e:
        debug(f"Megg error: {e}")
        return ""


async def call_claude(prompt: str, session_id: str = None, continue_last: bool = False, include_megg: bool = True) -> tuple[str, str, dict]:
    """
    Call Claude Code and return (response, session_id, metadata).
    metadata includes: cost, num_turns, duration
    """
    # Ensure sandbox exists
    Path(SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

    # Load megg context for new sessions (like the hook does)
    full_prompt = prompt
    if include_megg and not continue_last and not session_id:
        megg_ctx = load_megg_context()
        if megg_ctx:
            full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{prompt}"
            debug("Prepended megg context to prompt")

    # Build command with persona and capabilities
    cmd = [
        "claude", "-p", full_prompt,
        "--output-format", "json",
        "--append-system-prompt", VOICE_PERSONA,
        "--allowedTools", "Read,Grep,Glob,WebSearch,WebFetch,Task,Bash,Edit,Write,Skill",
        "--add-dir", CLAUDE_WORKING_DIR,  # Can read from anywhere in /home/dev
    ]

    if continue_last:
        cmd.append("--continue")
    elif session_id:
        cmd.extend(["--resume", session_id])

    debug(f"Calling Claude: prompt={len(prompt)} chars, continue={continue_last}, session={session_id[:8] if session_id else 'new'}...")
    debug(f"Working dir: {SANDBOX_DIR} (sandbox)")
    debug(f"Read access: {CLAUDE_WORKING_DIR}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd=SANDBOX_DIR  # Execute in sandbox, but can read from CLAUDE_WORKING_DIR
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                metadata = {
                    "cost": data.get("total_cost_usd", 0),
                    "num_turns": data.get("num_turns", 1),
                    "duration_ms": data.get("duration_ms", 0),
                }
                debug(f"Claude responded: {len(data.get('result', ''))} chars, {metadata['num_turns']} turns, ${metadata['cost']:.4f}")
                return data.get("result", result.stdout), data.get("session_id", session_id), metadata
            except json.JSONDecodeError:
                return result.stdout, session_id, {}
        else:
            debug(f"Claude error: {result.stderr[:100]}")
            return f"Error: {result.stderr}", session_id, {}

    except subprocess.TimeoutExpired:
        return "Task timed out after 5 minutes.", session_id, {}
    except Exception as e:
        return f"Error calling Claude: {e}", session_id, {}


# ============ Command Handlers ============

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Claude Voice Assistant\n\n"
        "Send me a voice message and I'll process it with Claude.\n\n"
        "Commands:\n"
        "/new [name] - Start new session\n"
        "/continue - Resume last session\n"
        "/sessions - List all sessions\n"
        "/switch <name> - Switch to session\n"
        "/status - Current session info"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start new session."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    session_name = " ".join(context.args) if context.args else None
    state["current_session"] = None  # Will be set on first message

    if session_name:
        await update.message.reply_text(f"New session started: {session_name}")
    else:
        await update.message.reply_text("New session started. Send a voice message to begin.")

    save_state()


async def cmd_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /continue command - resume last session."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    if state["current_session"]:
        await update.message.reply_text(f"Continuing session: {state['current_session'][:8]}...")
    else:
        await update.message.reply_text("No previous session. Send a voice message to start.")


async def cmd_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sessions command - list all sessions."""
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    if not state["sessions"]:
        await update.message.reply_text("No sessions yet.")
        return

    msg = "Sessions:\n"
    for i, sess in enumerate(state["sessions"][-10:], 1):  # Last 10
        current = " (current)" if sess == state["current_session"] else ""
        msg += f"{i}. {sess[:8]}...{current}\n"

    await update.message.reply_text(msg)


async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /switch command - switch to specific session."""
    if not context.args:
        await update.message.reply_text("Usage: /switch <session_id>")
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    session_id = context.args[0]

    # Find matching session
    matches = [s for s in state["sessions"] if s.startswith(session_id)]

    if len(matches) == 1:
        state["current_session"] = matches[0]
        save_state()
        await update.message.reply_text(f"Switched to session: {matches[0][:8]}...")
    elif len(matches) > 1:
        await update.message.reply_text(f"Multiple matches. Be more specific.")
    else:
        await update.message.reply_text(f"Session not found: {session_id}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show current session info."""
    debug(f"STATUS command from user {update.effective_user.id}")
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    if state["current_session"]:
        await update.message.reply_text(
            f"Current session: {state['current_session'][:8]}...\n"
            f"Total sessions: {len(state['sessions'])}"
        )
    else:
        await update.message.reply_text("No active session. Send a voice message or /new to start.")


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /health command - check all systems."""
    debug(f"HEALTH command from user {update.effective_user.id}, chat {update.effective_chat.id}, topic {update.message.message_thread_id}")

    status = []
    status.append("=== Health Check ===\n")

    # Check ElevenLabs
    try:
        test_audio = elevenlabs.text_to_speech.convert(
            text="test",
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_turbo_v2_5",
        )
        size = sum(len(c) for c in test_audio if isinstance(c, bytes))
        status.append(f"ElevenLabs TTS: OK ({size} bytes, turbo_v2_5)")
    except Exception as e:
        status.append(f"ElevenLabs TTS: FAILED - {e}")

    # Check Claude
    try:
        result = subprocess.run(
            ["claude", "-p", "Say OK", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/home/dev"
        )
        if result.returncode == 0:
            status.append("Claude Code: OK")
        else:
            status.append(f"Claude Code: FAILED - {result.stderr[:50]}")
    except Exception as e:
        status.append(f"Claude Code: FAILED - {e}")

    # Session info
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    status.append(f"\nSessions: {len(state['sessions'])}")
    status.append(f"Current: {state['current_session'][:8] if state['current_session'] else 'None'}...")

    # Sandbox info
    status.append(f"\nSandbox: {SANDBOX_DIR}")
    status.append(f"Sandbox exists: {Path(SANDBOX_DIR).exists()}")

    # Chat info
    status.append(f"\nChat ID: {update.effective_chat.id}")
    status.append(f"Topic ID: {update.message.message_thread_id or 'None'}")
    status.append(f"User ID: {update.effective_user.id}")

    await update.message.reply_text("\n".join(status))


# ============ Voice Handler ============

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    debug(f"VOICE received from user {update.effective_user.id}, chat {update.effective_chat.id}, topic {update.message.message_thread_id}")
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    # Acknowledge receipt
    processing_msg = await update.message.reply_text("Processing voice message...")
    debug("Sent processing acknowledgement")

    try:
        # Download voice
        voice = await update.message.voice.get_file()
        voice_bytes = await voice.download_as_bytearray()

        # Transcribe
        await processing_msg.edit_text("Transcribing...")
        text = await transcribe_voice(bytes(voice_bytes))

        if text.startswith("[Transcription error"):
            await processing_msg.edit_text(text)
            return

        # Show what was heard
        await processing_msg.edit_text(f"Heard: {text[:100]}{'...' if len(text) > 100 else ''}\n\nAsking Claude...")

        # Call Claude
        continue_last = state["current_session"] is not None
        response, new_session_id, metadata = await call_claude(
            text,
            session_id=state["current_session"],
            continue_last=continue_last
        )

        # Update session state
        if new_session_id and new_session_id != state["current_session"]:
            state["current_session"] = new_session_id
            if new_session_id not in state["sessions"]:
                state["sessions"].append(new_session_id)
            save_state()

        # Send text response (split if too long)
        await send_long_message(update, processing_msg, response)

        # Generate and send full voice response
        audio = await text_to_speech(response)
        if audio:
            await update.message.reply_voice(voice=audio)

    except Exception as e:
        debug(f"Error in handle_voice: {e}")
        await processing_msg.edit_text(f"Error: {e}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (same flow as voice, skip transcription)."""
    debug(f"TEXT received: '{update.message.text[:50]}' from user {update.effective_user.id}, chat {update.effective_chat.id}, topic {update.message.message_thread_id}")
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    text = update.message.text

    processing_msg = await update.message.reply_text("Asking Claude...")
    debug("Sent processing acknowledgement")

    try:
        continue_last = state["current_session"] is not None
        response, new_session_id, metadata = await call_claude(
            text,
            session_id=state["current_session"],
            continue_last=continue_last
        )

        if new_session_id and new_session_id != state["current_session"]:
            state["current_session"] = new_session_id
            if new_session_id not in state["sessions"]:
                state["sessions"].append(new_session_id)
            save_state()

        # Split long responses into multiple messages
        await send_long_message(update, processing_msg, response)

        # Also send voice response (V always speaks)
        audio = await text_to_speech(response)
        if audio:
            await update.message.reply_voice(voice=audio)

    except Exception as e:
        debug(f"Error in handle_text: {e}")
        await processing_msg.edit_text(f"Error: {e}")


def main():
    """Main entry point."""
    load_state()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("continue", cmd_continue))
    app.add_handler(CommandHandler("sessions", cmd_sessions))
    app.add_handler(CommandHandler("switch", cmd_switch))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("health", cmd_health))

    # Messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Ensure sandbox exists at startup
    Path(SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

    debug("Bot starting...")
    debug(f"Persona: V (brilliant, cynical voice assistant)")
    debug(f"TTS: eleven_turbo_v2_5 with expressive settings")
    debug(f"Sandbox: {SANDBOX_DIR}")
    debug(f"Read access: {CLAUDE_WORKING_DIR}")
    debug(f"Chat ID: {ALLOWED_CHAT_ID}")
    debug(f"Topic ID: {TOPIC_ID}")
    print("V is ready. Waiting for messages...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
