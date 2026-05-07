# =============================================================================
# LUMORA AI BACKEND - ADVANCED SINGLE FILE FOR REAL USERS
# Version: 9.0.0-real-users-groq-hf-tavily
#
# File name: main.py
#
# What this backend supports:
#   GET  /
#   GET  /health
#   GET  /models
#   GET  /usage
#   GET  /dashboard/features
#   GET  /image-health
#   GET  /video-health
#   GET  /search-test?q=...
#
#   POST /chat
#   POST /chat-fast
#   POST /chat-long
#   POST /study-plan
#   POST /quiz-generator
#   POST /flashcards
#   POST /research-helper
#   POST /image
#   POST /video
#   POST /generate
#
# Designed for Lumora Flutter Web:
#   - Chat routes always return {"reply": "..."}
#   - Image route returns {"image_base64": "..."}
#   - Video route returns {"video_base64": "..."}
#
# Providers:
#   - Groq for fast text/chat
#   - Hugging Face Router as text fallback
#   - Hugging Face for image and video
#   - Tavily for optional web search
#
# Required packages:
#   fastapi
#   uvicorn
#   pydantic
#   requests
#   groq
#   huggingface_hub
#   pillow
#
# Local run:
#   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
#
# PowerShell example:
#   cd C:\Users\mding\lumora_ai\backend
#   $env:GROQ_API_KEY="gsk_your_key_here"
#   $env:GROQ_MODEL="openai/gpt-oss-20b"
#   $env:GROQ_FAST_MODEL="llama-3.1-8b-instant"
#   $env:GROQ_BACKUP_MODEL="llama-3.3-70b-versatile"
#   $env:HF_TOKEN="hf_your_key_here"
#   $env:HF_MODEL="meta-llama/Llama-3.1-8B-Instruct"
#   $env:HF_BACKUP_MODEL="Qwen/Qwen2.5-3B-Instruct"
#   $env:HF_IMAGE_MODEL="black-forest-labs/FLUX.1-dev"
#   $env:HF_VIDEO_MODEL="Wan-AI/Wan2.2-T2V-A14B"
#   $env:HF_VIDEO_PROVIDER="fal-ai"
#   $env:TAVILY_API_KEY="tvly_your_key_here"
#   python -m uvicorn main:app --reload
#
# Railway variables:
#   GROQ_API_KEY
#   GROQ_MODEL
#   GROQ_FAST_MODEL
#   GROQ_BACKUP_MODEL
#   HF_TOKEN
#   HF_MODEL
#   HF_BACKUP_MODEL
#   HF_IMAGE_MODEL
#   HF_VIDEO_MODEL
#   HF_VIDEO_PROVIDER
#   TAVILY_API_KEY
#   NETLIFY_SITE
#   AI_PROVIDER=auto
# =============================================================================

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =============================================================================
# CONFIG
# =============================================================================

APP_NAME = "Lumora AI Backend"
APP_VERSION = "9.0.0-real-users-groq-hf-tavily"

ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
NETLIFY_SITE = os.getenv("NETLIFY_SITE", "https://lumora-study.netlify.app").strip().rstrip("/")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", NETLIFY_SITE).strip().rstrip("/")

# Optional simple protection.
# Leave empty for public frontend.
# If set, frontend must send header: X-Lumora-App-Key.
LUMORA_APP_KEY = os.getenv("LUMORA_APP_KEY", "").strip()

# Provider control:
#   auto = Groq first, Hugging Face text fallback
#   groq = Groq only
#   hf = Hugging Face text only
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()

# Groq text models
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant").strip()
GROQ_BACKUP_MODEL = os.getenv("GROQ_BACKUP_MODEL", "llama-3.3-70b-versatile").strip()

# Hugging Face text fallback + image/video
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
HF_BACKUP_MODEL = os.getenv("HF_BACKUP_MODEL", "Qwen/Qwen2.5-3B-Instruct").strip()
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev").strip()
HF_VIDEO_MODEL = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-T2V-A14B").strip()
HF_VIDEO_PROVIDER = os.getenv("HF_VIDEO_PROVIDER", "fal-ai").strip()
HF_ROUTER_URL = os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions").strip()

# Tavily search
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
TAVILY_SEARCH_URL = os.getenv("TAVILY_SEARCH_URL", "https://api.tavily.com/search").strip()

# Response settings
DEFAULT_MAX_TOKENS = int(os.getenv("LUMORA_MAX_TOKENS", "1100"))
FAST_MAX_TOKENS = int(os.getenv("LUMORA_FAST_MAX_TOKENS", "650"))
LONG_MAX_TOKENS = int(os.getenv("LUMORA_LONG_MAX_TOKENS", "2200"))
DEFAULT_TEMPERATURE = float(os.getenv("LUMORA_TEMPERATURE", "0.25"))

# Cache
CACHE_TTL_SECONDS = int(os.getenv("LUMORA_CACHE_TTL_SECONDS", "900"))
CACHE_MAX_ITEMS = int(os.getenv("LUMORA_CACHE_MAX_ITEMS", "250"))

# Real-user protection
RATE_LIMIT_CHAT_PER_MINUTE = int(os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "40"))
RATE_LIMIT_IMAGE_PER_HOUR = int(os.getenv("RATE_LIMIT_IMAGE_PER_HOUR", "20"))
RATE_LIMIT_VIDEO_PER_HOUR = int(os.getenv("RATE_LIMIT_VIDEO_PER_HOUR", "5"))
RATE_LIMIT_SEARCH_PER_MINUTE = int(os.getenv("RATE_LIMIT_SEARCH_PER_MINUTE", "15"))

MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "10"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "12000"))
MAX_PROMPT_CHARS_IMAGE = int(os.getenv("MAX_PROMPT_CHARS_IMAGE", "3000"))
MAX_PROMPT_CHARS_VIDEO = int(os.getenv("MAX_PROMPT_CHARS_VIDEO", "2500"))

# Timeouts
GROQ_TIMEOUT_SECONDS = int(os.getenv("GROQ_TIMEOUT_SECONDS", "60"))
HF_TEXT_TIMEOUT_SECONDS = int(os.getenv("HF_TEXT_TIMEOUT_SECONDS", "75"))
TAVILY_TIMEOUT_SECONDS = int(os.getenv("TAVILY_TIMEOUT_SECONDS", "25"))
HF_IMAGE_TIMEOUT_SECONDS = int(os.getenv("HF_IMAGE_TIMEOUT_SECONDS", "180"))
HF_VIDEO_TIMEOUT_SECONDS = int(os.getenv("HF_VIDEO_TIMEOUT_SECONDS", "420"))


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Advanced production-style Lumora AI backend for Flutter Web and real users.",
)

ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    NETLIFY_SITE,
    "https://lumora-study.netlify.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:12345",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:12345",
]

# Public Flutter Web mode. If you later add cookie auth, replace "*" with ALLOWED_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# IN-MEMORY STORAGE
# =============================================================================

_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}
_USAGE: Dict[str, Dict[str, Any]] = {}
_RATE_BUCKETS: Dict[str, List[float]] = {}
_REQUEST_LOG: List[Dict[str, Any]] = []


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    mode: str = "study"
    history: List[Dict[str, Any]] = Field(default_factory=list)
    long_answer: bool = False
    use_search: Optional[bool] = None
    user_id: Optional[str] = None


class ImageRequest(BaseModel):
    prompt: str
    style: str = "clean 3D science illustration"
    width: int = 1024
    height: int = 1024
    negative_prompt: str = "blurry, low quality, distorted, watermark, text artifacts, unreadable text"


class VideoRequest(BaseModel):
    prompt: str
    style: str = "professional educational video"
    seconds: int = 4
    negative_prompt: str = "blurry, low quality, distorted, watermark, flickering, text artifacts"


class StudyPlanRequest(BaseModel):
    topic: str
    days: int = 7
    level: str = "beginner"
    minutes_per_day: int = 45
    goal: str = ""


class QuizRequest(BaseModel):
    topic: str
    level: str = "beginner"
    questions: int = 10
    question_type: str = "multiple choice"
    notes: str = ""


class FlashcardRequest(BaseModel):
    topic: str
    level: str = "beginner"
    cards: int = 10
    notes: str = ""


class ResearchRequest(BaseModel):
    topic: str
    level: str = "college"
    use_search: bool = True
    requirements: str = ""


# =============================================================================
# GENERAL UTILITIES
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_zone_now(zone_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(zone_name))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone.utc)


def normalize_text(text: Any) -> str:
    return str(text or "").strip()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def make_request_id() -> str:
    return str(uuid.uuid4())


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def get_user_key(request: Request, user_id: Optional[str] = None) -> str:
    header_user = request.headers.get("x-lumora-user-id", "").strip()
    if user_id:
        return f"user:{user_id.strip()}"
    if header_user:
        return f"user:{header_user}"
    return f"ip:{client_ip(request)}"


def contains_any(text: str, keywords: List[str]) -> bool:
    lower = normalize_text(text).lower()
    return any(k.lower() in lower for k in keywords)


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = default
    return max(minimum, min(maximum, number))


def clamp_dimension(value: Any) -> int:
    # Keep output reasonable for real users and avoid huge API bills.
    return clamp_int(value, 1024, 256, 1024)


def clamp_video_seconds(value: Any) -> int:
    return clamp_int(value, 4, 2, 8)


def clean_user_message(message: str, max_chars: int = MAX_MESSAGE_CHARS) -> str:
    clean = normalize_text(message)
    clean = re.sub(r"\x00", "", clean)
    if len(clean) > max_chars:
        clean = clean[:max_chars]
    return clean


def limit_history(history: List[Dict[str, Any]], max_items: int = MAX_HISTORY_ITEMS) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    for item in (history or [])[-max_items:]:
        role = normalize_text(item.get("role", "user")).lower()
        content = normalize_text(item.get("content", ""))

        if role not in ["user", "assistant"]:
            role = "user"

        if content:
            cleaned.append({"role": role, "content": content[:1800]})
    return cleaned


def now_context() -> str:
    eastern = safe_zone_now("America/New_York")
    central = safe_zone_now("America/Chicago")
    return (
        f"Eastern Time: {eastern.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"Central Time: {central.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"UTC: {datetime.now(timezone.utc).isoformat()}"
    )


def log_event(event_type: str, data: Dict[str, Any]) -> None:
    item = {
        "time": utc_now(),
        "type": event_type,
        "data": data,
    }
    _REQUEST_LOG.append(item)
    if len(_REQUEST_LOG) > 700:
        del _REQUEST_LOG[:200]


def track_usage(user_key: str, kind: str, success: bool = True) -> None:
    safe_key = hash_text(user_key)

    if safe_key not in _USAGE:
        _USAGE[safe_key] = {
            "first_seen": utc_now(),
            "last_seen": utc_now(),
            "chat_requests": 0,
            "image_requests": 0,
            "video_requests": 0,
            "search_requests": 0,
            "errors": 0,
        }

    item = _USAGE[safe_key]
    item["last_seen"] = utc_now()

    if kind == "chat":
        item["chat_requests"] += 1
    elif kind == "image":
        item["image_requests"] += 1
    elif kind == "video":
        item["video_requests"] += 1
    elif kind == "search":
        item["search_requests"] += 1

    if not success:
        item["errors"] += 1


def check_app_key(request: Request) -> None:
    if not LUMORA_APP_KEY:
        return
    provided = request.headers.get("x-lumora-app-key", "").strip()
    if provided != LUMORA_APP_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing Lumora app key.")


def rate_limit(user_key: str, action: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    safe_key = hash_text(user_key)
    bucket_key = f"{safe_key}:{action}:{window_seconds}"

    items = _RATE_BUCKETS.get(bucket_key, [])
    items = [t for t in items if now - t < window_seconds]

    if len(items) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached for {action}. Please wait and try again.",
        )

    items.append(now)
    _RATE_BUCKETS[bucket_key] = items


# =============================================================================
# CACHE
# =============================================================================

def should_search_internet(message: str) -> bool:
    keywords = [
        "search internet",
        "search online",
        "search the web",
        "look up",
        "google",
        "latest",
        "current news",
        "recent news",
        "news today",
        "price today",
        "current price",
        "who is the current",
        "what is happening",
        "new update",
        "today",
        "this week",
        "this month",
        "2026",
        "2027",
    ]
    return contains_any(message, keywords)


def cache_key(message: str, mode: str, fast: bool, long_answer: bool) -> str:
    value = f"{mode.lower().strip()}|fast={fast}|long={long_answer}|{message.lower().strip()}"
    return hash_text(value)


def get_cached_reply(message: str, mode: str, fast: bool, long_answer: bool) -> Optional[str]:
    key = cache_key(message, mode, fast, long_answer)
    item = _RESPONSE_CACHE.get(key)
    if not item:
        return None

    created_at, reply = item
    if time.time() - created_at > CACHE_TTL_SECONDS:
        _RESPONSE_CACHE.pop(key, None)
        return None

    return reply


def set_cached_reply(message: str, mode: str, fast: bool, long_answer: bool, reply: str) -> None:
    if should_search_internet(message):
        return

    if len(_RESPONSE_CACHE) >= CACHE_MAX_ITEMS:
        oldest_key = min(_RESPONSE_CACHE, key=lambda k: _RESPONSE_CACHE[k][0])
        _RESPONSE_CACHE.pop(oldest_key, None)

    _RESPONSE_CACHE[cache_key(message, mode, fast, long_answer)] = (time.time(), reply)


# =============================================================================
# BASIC ROUTES
# =============================================================================

@app.get("/")
def home() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "message": "Lumora AI backend is running.",
        "frontend": NETLIFY_SITE,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "models": "/models",
            "chat": "/chat",
            "chat_fast": "/chat-fast",
            "chat_long": "/chat-long",
            "image": "/image",
            "video": "/video",
            "features": "/dashboard/features",
        },
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "frontend": NETLIFY_SITE,
        "cors": "open_for_flutter_web",
        "security": {
            "app_key_enabled": bool(LUMORA_APP_KEY),
        },
        "provider_mode": AI_PROVIDER,
        "groq": {
            "key_set": bool(GROQ_API_KEY),
            "primary_model": GROQ_MODEL,
            "fast_model": GROQ_FAST_MODEL,
            "backup_model": GROQ_BACKUP_MODEL,
        },
        "huggingface": {
            "token_set": bool(HF_TOKEN),
            "text_model": HF_MODEL,
            "backup_text_model": HF_BACKUP_MODEL,
            "image_model": HF_IMAGE_MODEL,
            "video_model": HF_VIDEO_MODEL,
            "video_provider": HF_VIDEO_PROVIDER,
        },
        "tavily": {
            "key_set": bool(TAVILY_API_KEY),
        },
        "limits": {
            "chat_per_minute": RATE_LIMIT_CHAT_PER_MINUTE,
            "search_per_minute": RATE_LIMIT_SEARCH_PER_MINUTE,
            "image_per_hour": RATE_LIMIT_IMAGE_PER_HOUR,
            "video_per_hour": RATE_LIMIT_VIDEO_PER_HOUR,
            "max_message_chars": MAX_MESSAGE_CHARS,
            "max_history_items": MAX_HISTORY_ITEMS,
        },
        "usage": {
            "active_users_observed": len(_USAGE),
            "cache_items": len(_RESPONSE_CACHE),
            "rate_buckets": len(_RATE_BUCKETS),
            "request_log_items": len(_REQUEST_LOG),
        },
        "time": {
            "utc": utc_now(),
            "eastern": safe_zone_now("America/New_York").isoformat(),
            "central": safe_zone_now("America/Chicago").isoformat(),
        },
    }


@app.get("/models")
def models() -> Dict[str, Any]:
    return {
        "ok": True,
        "provider_mode": AI_PROVIDER,
        "text_providers": {
            "primary": "Groq",
            "fallback": "Hugging Face Router",
        },
        "groq_models": {
            "primary": GROQ_MODEL,
            "fast": GROQ_FAST_MODEL,
            "backup": GROQ_BACKUP_MODEL,
        },
        "huggingface_models": {
            "text": HF_MODEL,
            "text_backup": HF_BACKUP_MODEL,
            "image": HF_IMAGE_MODEL,
            "video": HF_VIDEO_MODEL,
            "video_provider": HF_VIDEO_PROVIDER,
        },
    }


@app.get("/usage")
def usage() -> Dict[str, Any]:
    totals = {
        "chat_requests": 0,
        "image_requests": 0,
        "video_requests": 0,
        "search_requests": 0,
        "errors": 0,
    }

    for item in _USAGE.values():
        for key in totals:
            totals[key] += int(item.get(key, 0))

    return {
        "ok": True,
        "active_users_observed": len(_USAGE),
        "totals": totals,
        "cache_items": len(_RESPONSE_CACHE),
        "request_log_items": len(_REQUEST_LOG),
    }


@app.get("/dashboard/features")
def dashboard_features() -> Dict[str, Any]:
    return {
        "ok": True,
        "features": [
            {
                "id": "chat",
                "title": "AI Chat",
                "description": "Fast tutoring, research, writing, coding, and data help.",
                "endpoint": "/chat-fast",
                "status": "active" if (GROQ_API_KEY or HF_TOKEN) else "missing_ai_key",
            },
            {
                "id": "study",
                "title": "Study Planner",
                "description": "Build personalized study plans.",
                "endpoint": "/study-plan",
                "status": "active",
            },
            {
                "id": "research",
                "title": "Research Helper",
                "description": "Create summaries, outlines, thesis ideas, and drafts.",
                "endpoint": "/research-helper",
                "status": "active",
            },
            {
                "id": "quiz",
                "title": "Quiz Generator",
                "description": "Generate quizzes with answers and explanations.",
                "endpoint": "/quiz-generator",
                "status": "active",
            },
            {
                "id": "cards",
                "title": "Flashcards",
                "description": "Generate Q/A cards from notes or topics.",
                "endpoint": "/flashcards",
                "status": "active",
            },
            {
                "id": "image",
                "title": "Image Generator",
                "description": "Generate educational images.",
                "endpoint": "/image",
                "status": "active" if HF_TOKEN else "missing_hf_token",
            },
            {
                "id": "video",
                "title": "Video Generator",
                "description": "Generate short educational videos.",
                "endpoint": "/video",
                "status": "experimental" if HF_TOKEN else "missing_hf_token",
            },
        ],
    }


# =============================================================================
# SEARCH
# =============================================================================

def tavily_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    if not TAVILY_API_KEY:
        return {
            "ok": False,
            "error": "TAVILY_API_KEY is missing.",
            "answer": "",
            "results": [],
        }

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": clamp_int(max_results, 5, 1, 8),
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=TAVILY_TIMEOUT_SECONDS)

        if response.status_code >= 400:
            return {
                "ok": False,
                "error": f"Search failed with status {response.status_code}: {response.text[:700]}",
                "answer": "",
                "results": [],
            }

        data = response.json()
        return {
            "ok": True,
            "answer": data.get("answer", ""),
            "results": data.get("results", []),
        }

    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Search timed out.", "answer": "", "results": []}
    except Exception as e:
        return {"ok": False, "error": f"Search error: {e}", "answer": "", "results": []}


def format_search_context(search_data: Dict[str, Any]) -> str:
    if not search_data.get("ok"):
        return f"Search unavailable: {search_data.get('error', 'Unknown error')}"

    answer = normalize_text(search_data.get("answer", ""))
    results = search_data.get("results", [])

    lines: List[str] = []
    if answer:
        lines.append("Search summary:")
        lines.append(answer)
        lines.append("")

    lines.append("Search results:")
    for index, item in enumerate(results, start=1):
        title = normalize_text(item.get("title", "No title"))
        url = normalize_text(item.get("url", ""))
        content = normalize_text(item.get("content", ""))
        lines.append(f"{index}. {title}")
        lines.append(f"URL: {url}")
        lines.append(f"Content: {content[:900]}")
        lines.append("")

    return "\n".join(lines).strip()


@app.get("/search-test")
def search_test(q: str, request: Request) -> Dict[str, Any]:
    check_app_key(request)
    user_key = get_user_key(request)
    rate_limit(user_key, "search", RATE_LIMIT_SEARCH_PER_MINUTE, 60)

    query = normalize_text(q)
    if not query:
        raise HTTPException(status_code=400, detail="Missing q parameter.")

    data = tavily_search(query)
    track_usage(user_key, "search", bool(data.get("ok")))

    return {
        "ok": data.get("ok"),
        "query": query,
        "answer": data.get("answer"),
        "results": data.get("results"),
        "error": data.get("error"),
    }


# =============================================================================
# QUICK REPLIES AND TASK DETECTION
# =============================================================================

def current_datetime_reply(message: str) -> Optional[str]:
    lower = message.lower().strip()

    if any(word in lower for word in ["latest", "news", "search", "internet", "online", "recent"]):
        return None

    date_words = ["date", "today date", "today's date", "current date", "what is today"]
    time_words = ["time", "current time", "what time", "clock"]

    wants_date = any(w in lower for w in date_words)
    wants_time = any(w in lower for w in time_words)

    if not wants_date and not wants_time:
        return None

    eastern = safe_zone_now("America/New_York")
    central = safe_zone_now("America/Chicago")

    if wants_date and not wants_time:
        return f"Today's date is {eastern.strftime('%A, %B %d, %Y')} Eastern Time."

    if wants_time and not wants_date:
        return f"The current time is {eastern.strftime('%I:%M %p')} Eastern Time."

    return (
        f"Eastern Time: {eastern.strftime('%A, %B %d, %Y at %I:%M %p')}.\n"
        f"Central Time: {central.strftime('%A, %B %d, %Y at %I:%M %p')}."
    )


def quick_reply(message: str) -> Optional[str]:
    quick = {
        "hi": "Hi! What are we working on today?",
        "hello": "Hello! What would you like to study, build, or research?",
        "hey": "Hey! What should Lumora help you with?",
        "thanks": "You're welcome!",
        "thank you": "You're welcome!",
    }
    return quick.get(message.lower().strip())


def is_flashcard_request(message: str) -> bool:
    lower = message.lower()
    return "flashcard" in lower or "flash card" in lower or "study cards" in lower


def is_quiz_request(message: str) -> bool:
    lower = message.lower()
    return "quiz" in lower or "multiple choice" in lower or "practice questions" in lower


def is_study_plan_request(message: str) -> bool:
    lower = message.lower()
    return "study plan" in lower or "study planner" in lower or "day-by-day" in lower


def is_research_request(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in ["research", "literature review", "academic paper", "thesis", "sources"])


def is_code_request(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in ["code", "python", "fastapi", "flutter", "dart", "sql", "debug", "error", "main.py"])


def is_image_request(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in ["image", "picture", "draw", "illustration", "diagram"])


def is_video_request(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in ["video", "animation", "short clip"])


# =============================================================================
# PROMPTS AND RESPONSE CLEANING
# =============================================================================

def system_prompt(mode: str, fast: bool = False, long_answer: bool = False) -> str:
    mode = (mode or "study").lower().strip()

    base = f"""
You are Lumora AI.

Identity:
- You are an AI study, research, writing, coding, data, quiz, flashcard, image-prompt, and video-prompt assistant.
- You support real students and real users.
- You are clear, practical, accurate, and easy to understand.

Current time context:
{now_context()}

Core rules:
1. Be clear, helpful, direct, and student-friendly.
2. Never start with "Certainly", "Sure", or "Of course".
3. Avoid excessive markdown.
4. Do not invent sources, URLs, current facts, laws, prices, or news.
5. If web search context is provided, use it for current information.
6. If the user asks for complete code, provide complete working code.
7. If math is involved, show steps clearly.
8. Keep browser-friendly text.
9. Never reveal or ask the user to paste private API keys publicly.
10. Do not use markdown bold symbols like **.
11. Match the user's educational level when provided.
"""

    if fast:
        base += """
Fast mode:
- Give a complete but shorter answer.
- Usually 8 to 18 lines unless code is requested.
- Avoid long introductions.
"""

    if long_answer:
        base += """
Long answer mode:
- Provide a complete, detailed answer.
- Use sections when helpful.
- Include examples, steps, and practical guidance.
"""

    mode_blocks = {
        "chat": "Chat mode: answer naturally and helpfully.",
        "study": "Study mode: explain like a patient tutor with examples.",
        "research": "Research mode: organize ideas, summarize findings, and help academic writing.",
        "quiz": "Quiz mode: create quizzes with answers and short explanations.",
        "cards": "Cards mode: create useful flashcards with clear Q/A pairs.",
        "image": "Image mode: help create strong prompts for educational images.",
        "video": "Video mode: help create short educational video prompts and scripts.",
        "writing": "Writing mode: improve clarity, grammar, tone, and structure.",
        "data": "Data mode: help with Python, SQL, Spark, statistics, ML, dashboards, and analytics.",
        "code": "Code mode: give working code, exact file names, and commands.",
        "general": "General mode: answer clearly and practically.",
    }

    base += "\n" + mode_blocks.get(mode, mode_blocks["general"])
    return base.strip()


def task_prompt(message: str) -> str:
    if is_flashcard_request(message):
        return """
The user wants flashcards.

Format:
Flashcard 1
Q: ...
A: ...

Rules:
- No long introduction.
- Make answers concise but useful.
- If a number is requested, match that number.
"""

    if is_quiz_request(message):
        return """
The user wants a quiz.

Return:
- numbered questions
- answer choices if appropriate
- correct answer
- short explanation

Do not add unnecessary introductions.
"""

    if is_study_plan_request(message):
        return """
The user wants a study plan.

Include:
- day-by-day schedule
- topics
- practice tasks
- review tasks
- final checkpoint
"""

    if is_research_request(message):
        return """
The user wants research help.

Include:
- clear structure
- main ideas
- possible subtopics
- cautious language
- do not invent citations
"""

    if is_code_request(message):
        return """
The user wants coding help.

Rules:
- Provide complete code when requested.
- Include file names.
- Include run commands.
- Explain fixes briefly.
- Do not omit important sections.
"""

    if is_image_request(message):
        return """
The user may want an image prompt.

If they want actual generation, tell them Lumora can use /image.
If they want a prompt, produce a strong prompt and negative prompt.
"""

    if is_video_request(message):
        return """
The user may want video generation.

If they want actual generation, tell them Lumora can use /video.
If they want a prompt/script, produce a short structured video prompt.
"""

    return "Answer the user clearly and practically."


def clean_response_text(text: str) -> str:
    if not text:
        return ""

    cleaned = str(text)

    replacements = {
        "**": "",
        "__": "",
        "\u00b1": "+/-",
        "\u00b2": "^2",
        "\u00b3": "^3",
        "\u221a": "sqrt",
        "\u00d7": "*",
        "\u2013": "-",
        "\u2014": "-",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\\pm": "+/-",
        "\\times": "*",
        "\\cdot": "*",
        "\\quad": " ",
    }

    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)

    # Keep most math readable in Flutter even if Math renderer fails.
    cleaned = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", cleaned)
    cleaned = re.sub(r"(?i)^\s*(certainly|sure|of course)[,!\.\s-]*", "", cleaned).strip()
    cleaned = re.sub(r"\n{4,}", "\n\n", cleaned)
    return cleaned.strip()


# =============================================================================
# AI TEXT PROVIDERS
# =============================================================================

def get_groq_client():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing.")
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError("Missing package: groq. Install with: pip install groq") from e
    return Groq(api_key=GROQ_API_KEY)


def call_groq_model(model_name: str, messages: List[Dict[str, str]], max_tokens: int) -> Dict[str, Any]:
    try:
        client = get_groq_client()
        started = time.time()

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=max_tokens,
                timeout=GROQ_TIMEOUT_SECONDS,
            )
        except TypeError:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=max_tokens,
            )

        elapsed = round(time.time() - started, 3)
        reply = response.choices[0].message.content

        return {
            "ok": True,
            "provider": "groq",
            "model": model_name,
            "reply": reply,
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        return {
            "ok": False,
            "provider": "groq",
            "model": model_name,
            "error": str(e),
        }


def call_hf_text_model(model_name: str, messages: List[Dict[str, str]], max_tokens: int) -> Dict[str, Any]:
    if not HF_TOKEN:
        return {
            "ok": False,
            "provider": "huggingface",
            "model": model_name,
            "error": "HF_TOKEN is missing.",
        }

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": max_tokens,
    }

    try:
        started = time.time()
        response = requests.post(
            HF_ROUTER_URL,
            headers=headers,
            json=payload,
            timeout=HF_TEXT_TIMEOUT_SECONDS,
        )
        elapsed = round(time.time() - started, 3)

        if response.status_code >= 400:
            return {
                "ok": False,
                "provider": "huggingface",
                "model": model_name,
                "error": f"HF Router status {response.status_code}: {response.text[:800]}",
            }

        data = response.json()

        reply = ""
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices:
                message_obj = choices[0].get("message", {})
                reply = message_obj.get("content", "") if isinstance(message_obj, dict) else ""
            if not reply:
                reply = data.get("generated_text", "") or data.get("reply", "")

        if not reply:
            return {
                "ok": False,
                "provider": "huggingface",
                "model": model_name,
                "error": f"Unexpected HF Router response: {str(data)[:800]}",
            }

        return {
            "ok": True,
            "provider": "huggingface",
            "model": model_name,
            "reply": reply,
            "elapsed_seconds": elapsed,
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "provider": "huggingface",
            "model": model_name,
            "error": "HF Router timed out.",
        }
    except Exception as e:
        return {
            "ok": False,
            "provider": "huggingface",
            "model": model_name,
            "error": str(e),
        }


def build_messages(
    message: str,
    mode: str,
    history: List[Dict[str, Any]],
    fast: bool,
    long_answer: bool,
    use_search: Optional[bool],
    request: Optional[Request] = None,
    user_key: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], bool]:
    used_search = False
    web_context = ""

    should_search = bool(use_search) if use_search is not None else should_search_internet(message)

    if should_search:
        if request is not None and user_key is not None:
            rate_limit(user_key, "search", RATE_LIMIT_SEARCH_PER_MINUTE, 60)
        data = tavily_search(message)
        web_context = format_search_context(data)
        used_search = bool(data.get("ok"))

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt(mode, fast=fast, long_answer=long_answer)},
        {"role": "system", "content": task_prompt(message)},
    ]

    if web_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Internet/search context is provided below. "
                    "Use it for current information. Include useful URLs from it when relevant.\n\n"
                    + web_context
                ),
            }
        )

    messages.extend(limit_history(history, max_items=3 if fast else MAX_HISTORY_ITEMS))
    messages.append({"role": "user", "content": message})

    return messages, used_search


def provider_model_plan(fast: bool) -> List[Tuple[str, str]]:
    plan: List[Tuple[str, str]] = []

    groq_preferred = GROQ_FAST_MODEL if fast else GROQ_MODEL
    groq_candidates = [groq_preferred, GROQ_MODEL, GROQ_BACKUP_MODEL]
    hf_candidates = [HF_MODEL, HF_BACKUP_MODEL]

    def add(provider: str, model: str) -> None:
        model = normalize_text(model)
        if model and (provider, model) not in plan:
            plan.append((provider, model))

    if AI_PROVIDER == "groq":
        for model in groq_candidates:
            add("groq", model)
    elif AI_PROVIDER in ["hf", "huggingface"]:
        for model in hf_candidates:
            add("huggingface", model)
    else:
        for model in groq_candidates:
            add("groq", model)
        for model in hf_candidates:
            add("huggingface", model)

    return plan


# =============================================================================
# MAIN TEXT ENGINE
# =============================================================================

def lumora_text_engine(
    request: Request,
    chat_request: ChatRequest,
    fast: bool = False,
    force_long: bool = False,
) -> Dict[str, Any]:
    check_app_key(request)

    request_id = make_request_id()
    user_key = get_user_key(request, chat_request.user_id)

    rate_limit(
        user_key=user_key,
        action="chat",
        limit=RATE_LIMIT_CHAT_PER_MINUTE,
        window_seconds=60,
    )

    message = clean_user_message(chat_request.message)
    mode = normalize_text(chat_request.mode) or "study"
    long_answer = bool(force_long or chat_request.long_answer)

    if not message:
        return {
            "ok": True,
            "reply": "Please type a message first.",
            "request_id": request_id,
        }

    date_reply = current_datetime_reply(message)
    if date_reply:
        track_usage(user_key, "chat", True)
        return {
            "ok": True,
            "reply": date_reply,
            "provider": "datetime",
            "model": "datetime-handler",
            "cached": False,
            "request_id": request_id,
        }

    quick = quick_reply(message)
    if quick:
        track_usage(user_key, "chat", True)
        return {
            "ok": True,
            "reply": quick,
            "provider": "quick_reply",
            "model": "quick-reply",
            "cached": False,
            "request_id": request_id,
        }

    cached = get_cached_reply(message, mode, fast, long_answer)
    if cached:
        track_usage(user_key, "chat", True)
        return {
            "ok": True,
            "reply": cached,
            "provider": "cache",
            "model": "cache",
            "cached": True,
            "request_id": request_id,
        }

    messages, used_search = build_messages(
        message=message,
        mode=mode,
        history=chat_request.history,
        fast=fast,
        long_answer=long_answer,
        use_search=chat_request.use_search,
        request=request,
        user_key=user_key,
    )

    if used_search:
        track_usage(user_key, "search", True)

    max_tokens = FAST_MAX_TOKENS if fast else LONG_MAX_TOKENS if long_answer else DEFAULT_MAX_TOKENS
    errors: List[str] = []

    for provider, model_name in provider_model_plan(fast=fast):
        if provider == "groq":
            result = call_groq_model(model_name, messages, max_tokens=max_tokens)
        else:
            result = call_hf_text_model(model_name, messages, max_tokens=max_tokens)

        if result.get("ok"):
            reply = clean_response_text(result.get("reply", ""))
            if not reply:
                errors.append(f"{provider}:{model_name}: empty reply")
                continue

            set_cached_reply(message, mode, fast, long_answer, reply)
            track_usage(user_key, "chat", True)

            log_event(
                "chat_success",
                {
                    "request_id": request_id,
                    "user_key_hash": hash_text(user_key),
                    "mode": mode,
                    "fast": fast,
                    "long_answer": long_answer,
                    "provider": provider,
                    "model": model_name,
                    "elapsed_seconds": result.get("elapsed_seconds"),
                    "used_search": used_search,
                },
            )

            return {
                "ok": True,
                "reply": reply,
                "provider": provider,
                "model": model_name,
                "cached": False,
                "request_id": request_id,
                "elapsed_seconds": result.get("elapsed_seconds"),
                "used_search": used_search,
            }

        errors.append(f"{provider}:{model_name}: {result.get('error')}")

    track_usage(user_key, "chat", False)

    reply = (
        "Lumora could not get a response from the AI engine.\n\n"
        "Please check:\n"
        "1. GROQ_API_KEY is set correctly if using Groq.\n"
        "2. HF_TOKEN is set correctly if using Hugging Face fallback.\n"
        "3. The selected model names are valid.\n"
        "4. Your provider rate limits or credits are not exhausted.\n\n"
        "Errors:\n" + "\n".join(errors)
    )

    log_event(
        "chat_error",
        {
            "request_id": request_id,
            "user_key_hash": hash_text(user_key),
            "errors": errors,
        },
    )

    return {
        "ok": False,
        "reply": reply,
        "provider": None,
        "model": None,
        "cached": False,
        "request_id": request_id,
        "errors": errors,
    }


# =============================================================================
# CHAT ROUTES
# =============================================================================

@app.post("/chat")
def chat(request_body: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_text_engine(request, request_body, fast=False, force_long=False)


@app.post("/chat-fast")
def chat_fast(request_body: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_text_engine(request, request_body, fast=True, force_long=False)


@app.post("/chat-long")
def chat_long(request_body: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_text_engine(request, request_body, fast=False, force_long=True)


@app.post("/generate")
def generate_alias(request_body: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_text_engine(request, request_body, fast=True, force_long=False)


# =============================================================================
# DEDICATED TOOL ROUTES
# =============================================================================

@app.post("/study-plan")
def study_plan(request_body: StudyPlanRequest, request: Request) -> Dict[str, Any]:
    days = clamp_int(request_body.days, 7, 1, 60)
    minutes = clamp_int(request_body.minutes_per_day, 45, 10, 300)

    prompt = (
        f"Create a complete {days}-day study plan.\n"
        f"Topic: {request_body.topic}\n"
        f"Level: {request_body.level}\n"
        f"Goal: {request_body.goal}\n"
        f"Minutes per day: {minutes}\n\n"
        "Include daily topics, practice tasks, review tasks, checkpoints, and final review."
    )
    chat_req = ChatRequest(message=prompt, mode="study", history=[], long_answer=True, use_search=False)
    return lumora_text_engine(request, chat_req, fast=False, force_long=True)


@app.post("/quiz-generator")
def quiz_generator(request_body: QuizRequest, request: Request) -> Dict[str, Any]:
    questions = clamp_int(request_body.questions, 10, 1, 60)
    prompt = (
        f"Create a {questions}-question quiz.\n"
        f"Topic: {request_body.topic}\n"
        f"Level: {request_body.level}\n"
        f"Question type: {request_body.question_type}\n"
        f"Notes: {request_body.notes}\n\n"
        "Include questions, answer choices when useful, correct answers, and short explanations."
    )
    chat_req = ChatRequest(message=prompt, mode="quiz", history=[], long_answer=True, use_search=False)
    return lumora_text_engine(request, chat_req, fast=False, force_long=True)


@app.post("/flashcards")
def flashcards(request_body: FlashcardRequest, request: Request) -> Dict[str, Any]:
    cards = clamp_int(request_body.cards, 10, 1, 100)
    prompt = (
        f"Create {cards} flashcards.\n"
        f"Topic: {request_body.topic}\n"
        f"Level: {request_body.level}\n"
        f"Notes: {request_body.notes}\n\n"
        "Use this exact format:\n"
        "Flashcard 1\nQ: ...\nA: ..."
    )
    chat_req = ChatRequest(message=prompt, mode="cards", history=[], long_answer=True, use_search=False)
    return lumora_text_engine(request, chat_req, fast=False, force_long=True)


@app.post("/research-helper")
def research_helper(request_body: ResearchRequest, request: Request) -> Dict[str, Any]:
    prompt = (
        f"Help me research this topic: {request_body.topic}\n"
        f"Level: {request_body.level}\n"
        f"Requirements: {request_body.requirements}\n\n"
        "Provide overview, research questions, thesis idea, outline, key points, and next steps. "
        "If search context is used, include useful URLs from the search results."
    )
    chat_req = ChatRequest(
        message=prompt,
        mode="research",
        history=[],
        long_answer=True,
        use_search=request_body.use_search,
    )
    return lumora_text_engine(request, chat_req, fast=False, force_long=True)


# =============================================================================
# IMAGE GENERATION
# =============================================================================

def build_image_prompt(prompt: str, style: str) -> str:
    return (
        f"{normalize_text(prompt)}. "
        f"Style: {normalize_text(style) or 'clean educational illustration'}. "
        "High quality, clean composition, sharp focus, professional educational visual, no watermark."
    )


@app.get("/image-health")
def image_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "hf_token_set": bool(HF_TOKEN),
        "model": HF_IMAGE_MODEL,
        "endpoint": "/image",
        "required_packages": ["huggingface_hub", "pillow"],
        "limits": {
            "max_width": 1024,
            "max_height": 1024,
            "per_hour": RATE_LIMIT_IMAGE_PER_HOUR,
        },
    }


def make_hf_inference_client_for_image():
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise RuntimeError("Missing package. Install: pip install huggingface_hub pillow") from e

    # Different huggingface_hub versions use token or api_key.
    try:
        return InferenceClient(token=HF_TOKEN, timeout=HF_IMAGE_TIMEOUT_SECONDS)
    except TypeError:
        return InferenceClient(api_key=HF_TOKEN, timeout=HF_IMAGE_TIMEOUT_SECONDS)


@app.post("/image")
def generate_image(request_body: ImageRequest, request: Request) -> Dict[str, Any]:
    check_app_key(request)

    request_id = make_request_id()
    user_key = get_user_key(request)

    rate_limit(
        user_key=user_key,
        action="image",
        limit=RATE_LIMIT_IMAGE_PER_HOUR,
        window_seconds=3600,
    )

    if not HF_TOKEN:
        track_usage(user_key, "image", False)
        return {
            "ok": False,
            "error": "HF_TOKEN is missing. Set HF_TOKEN in your backend environment.",
            "request_id": request_id,
        }

    prompt = clean_user_message(request_body.prompt, MAX_PROMPT_CHARS_IMAGE)
    if not prompt:
        return {
            "ok": False,
            "error": "Please provide an image prompt.",
            "request_id": request_id,
        }

    width = clamp_dimension(request_body.width)
    height = clamp_dimension(request_body.height)
    final_prompt = build_image_prompt(prompt, request_body.style)

    try:
        started = time.time()
        client = make_hf_inference_client_for_image()

        image = client.text_to_image(
            prompt=final_prompt,
            model=HF_IMAGE_MODEL,
            width=width,
            height=height,
            negative_prompt=request_body.negative_prompt,
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        elapsed = round(time.time() - started, 3)

        track_usage(user_key, "image", True)
        log_event(
            "image_success",
            {
                "request_id": request_id,
                "model": HF_IMAGE_MODEL,
                "elapsed_seconds": elapsed,
            },
        )

        return {
            "ok": True,
            "model": HF_IMAGE_MODEL,
            "prompt": final_prompt,
            "width": width,
            "height": height,
            "mime_type": "image/png",
            "image_base64": image_base64,
            "request_id": request_id,
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        track_usage(user_key, "image", False)
        log_event("image_error", {"request_id": request_id, "error": str(e)})
        return {
            "ok": False,
            "error": f"Image generation failed: {e}",
            "model": HF_IMAGE_MODEL,
            "request_id": request_id,
        }


# =============================================================================
# VIDEO GENERATION
# =============================================================================

def build_video_prompt(prompt: str, style: str, seconds: int) -> str:
    return (
        f"{normalize_text(prompt)}. "
        f"Style: {normalize_text(style) or 'professional educational video'}. "
        f"Short {seconds}-second educational video, smooth motion, stable camera, high quality, no watermark."
    )


def bytes_from_video_result(video_result: Any) -> bytes:
    if isinstance(video_result, bytes):
        return video_result
    if isinstance(video_result, bytearray):
        return bytes(video_result)
    if hasattr(video_result, "read"):
        return bytes(video_result.read())
    if hasattr(video_result, "blob"):
        return bytes(video_result.blob)
    if hasattr(video_result, "content"):
        return bytes(video_result.content)
    if isinstance(video_result, str):
        # Some providers may return a URL. Fetch it.
        if video_result.startswith("http"):
            r = requests.get(video_result, timeout=HF_VIDEO_TIMEOUT_SECONDS)
            r.raise_for_status()
            return r.content
    raise TypeError(f"Unsupported video response type: {type(video_result)}")


@app.get("/video-health")
def video_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "hf_token_set": bool(HF_TOKEN),
        "model": HF_VIDEO_MODEL,
        "provider": HF_VIDEO_PROVIDER,
        "endpoint": "/video",
        "required_packages": ["huggingface_hub"],
        "limits": {
            "seconds_min": 2,
            "seconds_max": 8,
            "per_hour": RATE_LIMIT_VIDEO_PER_HOUR,
        },
        "note": "Video generation is experimental and can be slow.",
    }


def make_hf_inference_client_for_video():
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise RuntimeError("Missing package. Install: pip install huggingface_hub") from e

    try:
        return InferenceClient(
            provider=HF_VIDEO_PROVIDER,
            api_key=HF_TOKEN,
            timeout=HF_VIDEO_TIMEOUT_SECONDS,
        )
    except TypeError:
        try:
            return InferenceClient(
                provider=HF_VIDEO_PROVIDER,
                token=HF_TOKEN,
                timeout=HF_VIDEO_TIMEOUT_SECONDS,
            )
        except TypeError:
            return InferenceClient(token=HF_TOKEN, timeout=HF_VIDEO_TIMEOUT_SECONDS)


@app.post("/video")
def generate_video(request_body: VideoRequest, request: Request) -> Dict[str, Any]:
    check_app_key(request)

    request_id = make_request_id()
    user_key = get_user_key(request)

    rate_limit(
        user_key=user_key,
        action="video",
        limit=RATE_LIMIT_VIDEO_PER_HOUR,
        window_seconds=3600,
    )

    if not HF_TOKEN:
        track_usage(user_key, "video", False)
        return {
            "ok": False,
            "error": "HF_TOKEN is missing. Set HF_TOKEN in your backend environment.",
            "request_id": request_id,
        }

    prompt = clean_user_message(request_body.prompt, MAX_PROMPT_CHARS_VIDEO)
    if not prompt:
        return {
            "ok": False,
            "error": "Please provide a video prompt.",
            "request_id": request_id,
        }

    seconds = clamp_video_seconds(request_body.seconds)
    final_prompt = build_video_prompt(prompt, request_body.style, seconds)

    try:
        started = time.time()
        client = make_hf_inference_client_for_video()

        video = client.text_to_video(final_prompt, model=HF_VIDEO_MODEL)
        video_bytes = bytes_from_video_result(video)
        video_base64 = base64.b64encode(video_bytes).decode("utf-8")
        elapsed = round(time.time() - started, 3)

        track_usage(user_key, "video", True)
        log_event(
            "video_success",
            {
                "request_id": request_id,
                "model": HF_VIDEO_MODEL,
                "provider": HF_VIDEO_PROVIDER,
                "elapsed_seconds": elapsed,
            },
        )

        return {
            "ok": True,
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
            "prompt": final_prompt,
            "seconds": seconds,
            "mime_type": "video/mp4",
            "video_base64": video_base64,
            "request_id": request_id,
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        track_usage(user_key, "video", False)
        log_event("video_error", {"request_id": request_id, "error": str(e)})
        return {
            "ok": False,
            "error": f"Video generation failed: {e}",
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
            "request_id": request_id,
        }


# =============================================================================
# ERROR HANDLING AND HEADERS
# =============================================================================

@app.middleware("http")
async def add_headers_and_timing(request: Request, call_next):
    started = time.time()
    request_id = make_request_id()

    try:
        response = await call_next(request)
        elapsed = round(time.time() - started, 4)
        response.headers["X-Lumora-Version"] = APP_VERSION
        response.headers["X-Lumora-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(elapsed)
        return response

    except HTTPException:
        raise

    except Exception as e:
        elapsed = round(time.time() - started, 4)
        log_event(
            "server_error",
            {
                "request_id": request_id,
                "path": request.url.path,
                "error": str(e),
                "elapsed_seconds": elapsed,
                "traceback": traceback.format_exc()[-2500:],
            },
        )
        raise


# =============================================================================
# LOCAL DEV
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
