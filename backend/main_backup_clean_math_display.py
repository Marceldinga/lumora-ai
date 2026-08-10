
# =============================================================================
# LUMORA AI BACKEND - COMPLETE SINGLE FILE
# Version: 12.6.0-json-verifier-fallback-fixed
#
# File name: main.py
#
# Main fix:
#   When Python calculation succeeds, /chat returns a deterministic math reply
#   from the calculation result instead of letting the LLM rewrite arithmetic.
#   This fixes the regression error where /calculate returned 286.424...
#   but /chat introduced a wrong intermediate value and broken Python syntax.
#
# Install:
#   pip install fastapi uvicorn pydantic requests groq pillow python-dotenv
#
# Run:
#   cd C:\Users\mding\lumora_ai\backend
#   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
#
# Test:
#   Invoke-RestMethod `
#     -Uri "http://127.0.0.1:8000/chat" `
#     -Method POST `
#     -ContentType "application/json" `
#     -Body '{"message":"regression x: 800,1000,1200,1500,1800 y: 150,180,220,270,320 predict:1600","mode":"math"}' |
#     ConvertTo-Json -Depth 10
# =============================================================================

from __future__ import annotations

import base64
import hashlib
import json
import ast
import math
import os
import re
import statistics
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
except Exception:
    sp = None

try:
    import numpy as np
except Exception:
    np = None

try:
    from PIL import Image
except Exception:
    Image = None


# =============================================================================
# CONFIG
# =============================================================================

APP_NAME = "Lumora AI Backend"
APP_VERSION = "12.7.7-final-quiz-repair-gate"

ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
NETLIFY_SITE = os.getenv("NETLIFY_SITE", "https://lumora-study.netlify.app").strip().rstrip("/")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", NETLIFY_SITE).strip().rstrip("/")
LUMORA_APP_KEY = os.getenv("LUMORA_APP_KEY", "").strip()

AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant").strip()
GROQ_BACKUP_MODEL = os.getenv("GROQ_BACKUP_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_VERIFIER_MODEL = os.getenv("GROQ_VERIFIER_MODEL", "llama-3.3-70b-versatile").strip()

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()
HF_BACKUP_MODEL = os.getenv("HF_BACKUP_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
HF_THIRD_MODEL = os.getenv("HF_THIRD_MODEL", "mistralai/Mistral-7B-Instruct-v0.3").strip()
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
HF_VIDEO_MODEL = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-T2V-A14B").strip()
HF_VIDEO_PROVIDER = os.getenv("HF_VIDEO_PROVIDER", "fal-ai").strip()
HF_ROUTER_URL = os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions").strip()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
TAVILY_SEARCH_URL = os.getenv("TAVILY_SEARCH_URL", "https://api.tavily.com/search").strip()

DEFAULT_MAX_TOKENS = int(os.getenv("LUMORA_MAX_TOKENS", "1200"))
FAST_MAX_TOKENS = int(os.getenv("LUMORA_FAST_MAX_TOKENS", "700"))
LONG_MAX_TOKENS = int(os.getenv("LUMORA_LONG_MAX_TOKENS", "2600"))
VERIFIER_MAX_TOKENS = int(os.getenv("LUMORA_VERIFIER_MAX_TOKENS", "1000"))
DEFAULT_TEMPERATURE = float(os.getenv("LUMORA_TEMPERATURE", "0.25"))
VERIFIER_TEMPERATURE = float(os.getenv("LUMORA_VERIFIER_TEMPERATURE", "0.0"))

BRAIN_ENABLED = os.getenv("BRAIN_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
BRAIN_VERIFY = os.getenv("BRAIN_VERIFY", "true").strip().lower() in {"1", "true", "yes", "on"}
BRAIN_MEMORY_MAX_ITEMS = int(os.getenv("BRAIN_MEMORY_MAX_ITEMS", "500"))
BRAIN_MIN_VERIFY_SCORE = int(os.getenv("BRAIN_MIN_VERIFY_SCORE", "75"))

CACHE_TTL_SECONDS = int(os.getenv("LUMORA_CACHE_TTL_SECONDS", "900"))
CACHE_MAX_ITEMS = int(os.getenv("LUMORA_CACHE_MAX_ITEMS", "250"))

RATE_LIMIT_CHAT_PER_MINUTE = int(os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "40"))
RATE_LIMIT_IMAGE_PER_HOUR = int(os.getenv("RATE_LIMIT_IMAGE_PER_HOUR", "20"))
RATE_LIMIT_VIDEO_PER_HOUR = int(os.getenv("RATE_LIMIT_VIDEO_PER_HOUR", "5"))
RATE_LIMIT_SEARCH_PER_MINUTE = int(os.getenv("RATE_LIMIT_SEARCH_PER_MINUTE", "15"))

MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "10"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "12000"))
MAX_PROMPT_CHARS_IMAGE = int(os.getenv("MAX_PROMPT_CHARS_IMAGE", "3000"))
MAX_PROMPT_CHARS_VIDEO = int(os.getenv("MAX_PROMPT_CHARS_VIDEO", "2500"))

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
    description="Lumora AI unified backend with Groq, Hugging Face, Tavily, Brain routing, memory, verification, and deterministic calculation replies.",
)

allowed_origins = [
    "*",
    NETLIFY_SITE,
    FRONTEND_ORIGIN,
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([x for x in allowed_origins if x])),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MEMORY
# =============================================================================

_RESPONSE_CACHE: Dict[str, Tuple[float, str]] = {}
_USAGE: Dict[str, Dict[str, Any]] = {}
_RATE_BUCKETS: Dict[str, List[float]] = {}
_REQUEST_LOG: List[Dict[str, Any]] = []
_LUMORA_BRAIN_MEMORY: List[Dict[str, Any]] = []


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
    verify: Optional[bool] = None


class CalculateRequest(BaseModel):
    message: str


class ImageRequest(BaseModel):
    prompt: str
    style: str = "clean 3D educational illustration"
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
# UTILITIES
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


def fmt_num(value: Any, digits: int = 6) -> str:
    try:
        x = float(value)
        if math.isfinite(x):
            if abs(x - round(x)) < 1e-12:
                return str(int(round(x)))
            return f"{x:.{digits}f}".rstrip("0").rstrip(".")
    except Exception:
        pass
    return str(value)


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
    _REQUEST_LOG.append({"time": utc_now(), "type": event_type, "data": data})
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


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = normalize_text(text)
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    raw = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


# =============================================================================
# CACHE
# =============================================================================

def should_search_internet(message: str) -> bool:
    keywords = [
        "search internet", "search online", "search the web", "look up", "google",
        "latest", "current news", "recent news", "news today", "price today",
        "current price", "who is the current", "what is happening", "new update",
        "today", "this week", "this month", "2026", "2027",
    ]
    return contains_any(message, keywords)


def cache_key(message: str, mode: str, fast: bool, long_answer: bool) -> str:
    value = f"{APP_VERSION}|{mode.lower().strip()}|fast={fast}|long={long_answer}|{message.lower().strip()}"
    return hash_text(value)


def get_cached_reply(message: str, mode: str, fast: bool, long_answer: bool) -> Optional[str]:
    if mode.lower().strip() in {"study", "quiz", "research", "math", "data"}:
        return None

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
    if mode.lower().strip() in {"study", "quiz", "research", "math", "data"}:
        return

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
        "message": "Lumora AI backend is running with deterministic Python calculation replies.",
        "frontend": NETLIFY_SITE,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "models": "/models",
            "usage": "/usage",
            "chat": "/chat",
            "chat_fast": "/chat-fast",
            "chat_long": "/chat-long",
            "brain_chat": "/brain-chat",
            "brain_memory": "/brain-memory",
            "calculate": "/calculate",
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
        "security": {"app_key_enabled": bool(LUMORA_APP_KEY)},
        "brain": {
            "enabled": BRAIN_ENABLED,
            "verification_enabled": BRAIN_VERIFY,
            "verifier_model": GROQ_VERIFIER_MODEL,
            "memory_items": len(_LUMORA_BRAIN_MEMORY),
            "latex_math": True,
            "deterministic_calculation_replies": True,
        },
        "provider_mode": AI_PROVIDER,
        "groq": {
            "key_set": bool(GROQ_API_KEY),
            "primary_model": GROQ_MODEL,
            "fast_model": GROQ_FAST_MODEL,
            "backup_model": GROQ_BACKUP_MODEL,
            "verifier_model": GROQ_VERIFIER_MODEL,
        },
        "huggingface": {
            "token_set": bool(HF_TOKEN),
            "text_model": HF_MODEL,
            "backup_text_model": HF_BACKUP_MODEL,
            "third_text_model": HF_THIRD_MODEL,
            "image_model": HF_IMAGE_MODEL,
            "video_model": HF_VIDEO_MODEL,
            "video_provider": HF_VIDEO_PROVIDER,
        },
        "python_calculation_engine": {
            "enabled": True,
            "version": "universal-v12.7-deterministic-lessons",
            "sympy_available": sp is not None,
            "numpy_available": np is not None,
            "subjects": [
                "math", "algebra", "calculus", "statistics", "physics",
                "chemistry", "engineering", "finance", "data science",
            ],
        },
        "tavily": {"key_set": bool(TAVILY_API_KEY)},
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
        "groq_models": {
            "primary": GROQ_MODEL,
            "fast": GROQ_FAST_MODEL,
            "backup": GROQ_BACKUP_MODEL,
            "verifier": GROQ_VERIFIER_MODEL,
        },
        "huggingface_models": {
            "text": HF_MODEL,
            "text_backup": HF_BACKUP_MODEL,
            "text_third": HF_THIRD_MODEL,
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
        "brain_memory_items": len(_LUMORA_BRAIN_MEMORY),
        "request_log_items": len(_REQUEST_LOG),
    }


@app.get("/brain-memory")
def brain_memory() -> Dict[str, Any]:
    return {
        "ok": True,
        "brain": "Lumora Brain v12.7.7",
        "memory_items": len(_LUMORA_BRAIN_MEMORY),
        "recent": _LUMORA_BRAIN_MEMORY[-10:],
    }


@app.get("/dashboard/features")
def dashboard_features() -> Dict[str, Any]:
    return {
        "ok": True,
        "features": [
            {
                "id": "brain",
                "title": "Lumora Brain v12.7.7",
                "description": "Unified router, memory, verification, search, LaTeX math, and deterministic calculation replies.",
                "endpoint": "/brain-chat",
                "status": "active" if BRAIN_ENABLED else "disabled",
            },
            {
                "id": "chat",
                "title": "AI Chat",
                "description": "Fast tutoring, research, writing, coding, and data help.",
                "endpoint": "/chat-fast",
                "status": "active" if (GROQ_API_KEY or HF_TOKEN) else "missing_ai_key",
            },
            {
                "id": "calculate",
                "title": "Python Calculation Engine",
                "description": "Regression, statistics, formulas, finance, physics, and engineering calculations.",
                "endpoint": "/calculate",
                "status": "active",
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
# PYTHON CALCULATION ENGINE
# =============================================================================

CALC_KEYWORDS = [
    "solve", "calculate", "compute", "evaluate", "simplify", "equation", "formula", "expression",
    "linear equation", "quadratic", "polynomial", "system of equations", "derivative", "differentiate",
    "integral", "integrate", "limit", "function", "gradient", "optimization",
    "mean", "median", "mode", "variance", "standard deviation", "probability", "regression",
    "correlation", "mse", "rmse", "mae", "r2", "statistics", "matrix", "tensor",
    "physics", "force", "velocity", "acceleration", "momentum", "energy", "work", "power",
    "torque", "projectile", "gravity", "newton", "kinetic", "potential",
    "chemistry", "moles", "molar mass", "stoichiometry", "ph", "gas law", "balance equation", "reaction",
    "engineering", "stress", "strain", "beam", "load", "circuit", "voltage", "current", "resistance",
    "ohm", "thermodynamics", "fluid mechanics", "heat transfer", "control system", "signal processing",
    "interest", "compound interest", "roi", "npv", "forecast", "growth rate", "discount rate",
    "machine learning", "data science", "algorithm complexity", "neural network", "gradient descent",
    "loss function", "backpropagation",
]


def is_conceptual_study_request(message: str) -> bool:
    """
    Study/explanation requests must NOT go to the Python calculation parser.

    Examples that should be STUDY:
      - Explain chemistry Group 2 elements.
      - Explain linear regression with a simple example.
      - What is machine learning?
      - Teach me photosynthesis.

    Examples that should be CALCULATION:
      - calculate force mass 1200 acceleration 3.5
      - regression x: 2,3,4 y: 5,6,7 predict:8
      - mean, median, variance for 10,20,30
    """
    text = normalize_text(message).lower()

    study_words = [
        "explain", "what is", "define", "definition", "teach",
        "simple example", "example", "overview", "how does",
        "why", "summarize", "in simple terms", "beginner",
        "help me understand", "lesson", "describe"
    ]

    calculation_markers = [
        "calculate", "compute", "solve", "evaluate", "predict:",
        "x:", "y:", "mean", "median", "variance", "standard deviation",
        "mse", "rmse", "mae", "r2", "correlation", "derivative",
        "integral", "compound interest"
    ]

    has_study_intent = any(word in text for word in study_words)
    has_calculation_intent = any(word in text for word in calculation_markers)

    return has_study_intent and not has_calculation_intent


def needs_python_calculation(message: str) -> bool:
    text = normalize_text(message).lower()

    # Universal study AI rule:
    # conceptual subject questions should go to the study tutor, not the calculator.
    if is_conceptual_study_request(message):
        return False

    # Direct arithmetic
    if re.search(r"\d+\s*[\+\-\*\/\^]\s*\d+", text):
        return True

    # Structured regression/data calculation
    try:
        if parse_regression_pairs(message):
            return True
    except Exception:
        pass

    # Explicit calculation intent only.
    explicit_calc_words = [
        "solve", "calculate", "compute", "evaluate", "predict:",
        "mean", "median", "variance", "standard deviation",
        "mse", "rmse", "mae", "r2", "correlation",
        "compound interest", "future value",
        "force", "kinetic energy", "ohm", "stress",
        "derivative", "differentiate", "integral", "integrate"
    ]

    return any(keyword in text for keyword in explicit_calc_words)

def extract_numbers(text: str) -> List[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]


def parse_number_list(text: str) -> List[float]:
    return extract_numbers(text)


def safe_eval_expression(expr: str) -> Optional[float]:
    allowed = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
        "abs": abs,
        "pow": pow,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
    }

    clean = normalize_text(expr).replace("^", "**")
    if not clean:
        return None

    if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s,a-zA-Z_]+", clean):
        return None

    try:
        value = eval(clean, {"__builtins__": {}}, allowed)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
        return None
    except Exception:
        return None


def extract_predict_values(message: str) -> List[float]:
    text = normalize_text(message)
    patterns = [
        r"predict\s*(?:y)?\s*(?:when|at|for)?\s*x?\s*[:=]?\s*(-?\d+(?:\.\d+)?)",
        r"when\s*x\s*=\s*(-?\d+(?:\.\d+)?)",
        r"for\s*x\s*=\s*(-?\d+(?:\.\d+)?)",
    ]
    values: List[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            try:
                values.append(float(match.group(1)))
            except Exception:
                pass
    return list(dict.fromkeys(values))


def parse_regression_pairs(message: str) -> Optional[Tuple[List[float], List[float]]]:
    text = normalize_text(message)

    label_map = {
        "x": r"(?:x|x\s+values?|sizes?|inputs?)",
        "y": r"(?:y|y\s+values?|prices?|outputs?|targets?)",
    }

    def values_after(label_regex: str, stop_regex: str) -> Optional[List[float]]:
        patterns = [
            rf"\b{label_regex}\b\s*[:=]\s*\[?(.+?)\]?\s*(?={stop_regex})",
            rf"\b{label_regex}\b\s+\[?(.+?)\]?\s*(?={stop_regex})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I | re.DOTALL)
            if match:
                values = parse_number_list(match.group(1))
                if values:
                    return values
        return None

    x_stop = rf"(?:\b{label_map['y']}\b\s*[:=]|\bpredict\b|\bwhen\b|\bfor\s+x\b|$)"
    y_stop = rf"(?:\b{label_map['x']}\b\s*[:=]|\bpredict\b|\bwhen\b|\bfor\s+x\b|$)"

    x_vals = values_after(label_map["x"], x_stop)
    y_vals = values_after(label_map["y"], y_stop)

    if x_vals and y_vals and len(x_vals) == len(y_vals) and len(x_vals) >= 2:
        return x_vals, y_vals

    nums = extract_numbers(text)
    predict_values = extract_predict_values(text)
    filtered_nums = nums[:]

    for pv in predict_values:
        for i in range(len(filtered_nums) - 1, -1, -1):
            if abs(filtered_nums[i] - pv) < 1e-12:
                filtered_nums.pop(i)
                break

    if len(filtered_nums) >= 4 and len(filtered_nums) % 2 == 0:
        half = len(filtered_nums) // 2
        x_vals = filtered_nums[:half]
        y_vals = filtered_nums[half:]
        if len(x_vals) == len(y_vals) and len(x_vals) >= 2:
            return x_vals, y_vals

    return None


def linear_regression_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    if "regression" not in text and "linear model" not in text and "best fit" not in text:
        return None

    pairs = parse_regression_pairs(message)
    if not pairs:
        return {
            "type": "linear_regression",
            "ok": False,
            "error": "Please provide paired x and y values.",
            "example": "regression x: 800,1000,1200 y: 150,180,220 predict:1600",
        }

    x, y = pairs
    n = len(x)

    if n != len(y) or n < 2:
        return {
            "type": "linear_regression",
            "ok": False,
            "error": "x and y must have the same length and at least 2 values.",
            "example": "regression x: 800,1000,1200 y: 150,180,220 predict:1600",
        }

    x_mean = sum(x) / n
    y_mean = sum(y) / n
    covariance_numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    x_variance_numerator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if abs(x_variance_numerator) < 1e-15:
        return {
            "type": "linear_regression",
            "ok": False,
            "error": "Regression failed because all x values are identical.",
        }

    slope = covariance_numerator / x_variance_numerator
    intercept = y_mean - slope * x_mean
    predictions = [slope * value + intercept for value in x]
    residuals = [y[i] - predictions[i] for i in range(n)]

    mse = sum(err ** 2 for err in residuals) / n
    rmse = math.sqrt(mse)
    mae = sum(abs(err) for err in residuals) / n

    ss_res = sum(err ** 2 for err in residuals)
    ss_tot = sum((value - y_mean) ** 2 for value in y)
    r2 = 1 - (ss_res / ss_tot) if abs(ss_tot) > 1e-15 else 1.0

    result: Dict[str, Any] = {
        "type": "linear_regression",
        "ok": True,
        "n": n,
        "x": x,
        "y": y,
        "x_mean": x_mean,
        "y_mean": y_mean,
        "covariance_numerator": covariance_numerator,
        "x_variance_numerator": x_variance_numerator,
        "slope": slope,
        "intercept": intercept,
        "equation": f"y = {slope:.6f}x + {intercept:.6f}",
        "predictions": predictions,
        "residuals": residuals,
        "mse": mse,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
    }

    requested = extract_predict_values(message)
    if requested:
        result["predictions_requested"] = {
            str(int(px) if abs(px - round(px)) < 1e-12 else px): slope * px + intercept
            for px in requested
        }

    return result


def statistics_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    if not any(k in text for k in ["mean", "median", "mode", "variance", "standard deviation", "stats", "statistics"]):
        return None

    values = extract_numbers(message)
    if not values:
        return {"type": "statistics", "ok": False, "error": "No numeric values were found."}

    result: Dict[str, Any] = {
        "type": "statistics",
        "ok": True,
        "count": len(values),
        "values": values,
        "mean": sum(values) / len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }

    try:
        result["mode"] = statistics.multimode(values)
    except Exception:
        pass

    if len(values) > 1:
        result["sample_variance"] = statistics.variance(values)
        result["sample_standard_deviation"] = statistics.stdev(values)
        result["population_variance"] = statistics.pvariance(values)
        result["population_standard_deviation"] = statistics.pstdev(values)

    return result


def finance_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    if "compound interest" not in text and "future value" not in text:
        return None

    nums = extract_numbers(message)
    if len(nums) < 3:
        return {
            "type": "compound_interest",
            "ok": False,
            "error": "Provide principal, annual rate, and time. Optional: compounding periods per year.",
            "example": "compound interest principal 1000 rate 5 years 3 n 12",
        }

    principal = nums[0]
    rate = nums[1] / 100 if nums[1] > 1 else nums[1]
    years = nums[2]
    n = nums[3] if len(nums) >= 4 else 1

    if n <= 0:
        return {"type": "compound_interest", "ok": False, "error": "Compounding periods per year must be positive."}

    amount = principal * (1 + rate / n) ** (n * years)
    interest = amount - principal

    return {
        "type": "compound_interest",
        "ok": True,
        "principal": principal,
        "annual_rate_decimal": rate,
        "years": years,
        "compounds_per_year": n,
        "future_value": amount,
        "interest_earned": interest,
        "formula": "A = P(1 + r/n)^(nt)",
    }


def physics_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    nums = extract_numbers(message)

    if ("force" in text or "newton" in text) and len(nums) >= 2:
        mass = nums[0]
        acceleration = nums[1]
        return {
            "type": "physics_force",
            "ok": True,
            "mass": mass,
            "acceleration": acceleration,
            "force": mass * acceleration,
            "formula": "F = ma",
        }

    if "kinetic energy" in text and len(nums) >= 2:
        mass = nums[0]
        velocity = nums[1]
        return {
            "type": "kinetic_energy",
            "ok": True,
            "mass": mass,
            "velocity": velocity,
            "kinetic_energy": 0.5 * mass * velocity ** 2,
            "formula": "KE = 1/2 mv^2",
        }

    return None


def engineering_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    nums = extract_numbers(message)

    if "ohm" in text or ("voltage" in text and "current" in text and "resistance" in text):
        if len(nums) >= 2:
            current = nums[0]
            resistance = nums[1]
            return {
                "type": "ohms_law",
                "ok": True,
                "current": current,
                "resistance": resistance,
                "voltage": current * resistance,
                "formula": "V = IR",
            }

    if "stress" in text and len(nums) >= 2:
        force = nums[0]
        area = nums[1]
        if area == 0:
            return {"type": "stress", "ok": False, "error": "Area cannot be zero."}
        return {
            "type": "stress",
            "ok": True,
            "force": force,
            "area": area,
            "stress": force / area,
            "formula": "stress = force / area",
        }

    return None


def expression_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message)
    patterns = [
        r"(?:calculate|compute|evaluate)\s+(.+)$",
        r"^\s*([-+*/().\d\s^a-zA-Z_,]+)\s*$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue

        expr = match.group(1).strip()
        if not re.search(r"\d", expr):
            continue

        value = safe_eval_expression(expr)
        if value is not None:
            return {"type": "expression", "ok": True, "expression": expr, "result": value}

    return None


def algebra_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    if sp is None:
        return None

    if "solve" not in text and "equation" not in text:
        return None

    raw = normalize_text(message)
    raw = re.sub(r"(?i)^solve\s+", "", raw).strip()

    if "=" not in raw:
        return None

    try:
        x = sp.Symbol("x")
        left, right = raw.split("=", 1)
        expr = sp.sympify(left.replace("^", "**")) - sp.sympify(right.replace("^", "**"))
        solutions = sp.solve(expr, x)
        return {
            "type": "algebra_solve",
            "ok": True,
            "equation": raw,
            "solutions": [str(s) for s in solutions],
        }
    except Exception:
        return None


def calculus_engine(message: str) -> Optional[Dict[str, Any]]:
    text = normalize_text(message).lower()
    if sp is None:
        return None

    raw = normalize_text(message)

    try:
        x = sp.Symbol("x")

        if "derivative" in text or "differentiate" in text or "derive" in text:
            patterns = [
                r"derivative\s+of\s+(.+)",
                r"find\s+the\s+derivative\s+of\s+(.+)",
                r"solve\s+the\s+derivative\s+of\s+(.+)",
                r"differentiate\s+(.+)",
                r"derive\s+(.+)",
            ]

            expr_text = ""
            for pattern in patterns:
                match = re.search(pattern, raw, flags=re.I)
                if match:
                    expr_text = match.group(1)
                    break

            if not expr_text:
                return None

            expr_text = expr_text.strip()
            expr_text = re.sub(r"^f\(x\)\s*=\s*", "", expr_text, flags=re.I)
            expr_text = expr_text.replace("^", "**")

            result = sp.diff(parse_expr(expr_text, transformations=standard_transformations + (implicit_multiplication_application,)), x)

            return {
                "type": "derivative",
                "ok": True,
                "expression": expr_text.replace("**", "^"),
                "variable": "x",
                "result": str(result).replace("**", "^"),
            }

        if "integral" in text or "integrate" in text:
            patterns = [
                r"integral\s+of\s+(.+)",
                r"find\s+the\s+integral\s+of\s+(.+)",
                r"integrate\s+(.+)",
            ]

            expr_text = ""
            for pattern in patterns:
                match = re.search(pattern, raw, flags=re.I)
                if match:
                    expr_text = match.group(1)
                    break

            if not expr_text:
                return None

            expr_text = expr_text.strip()
            expr_text = re.sub(r"^f\(x\)\s*=\s*", "", expr_text, flags=re.I)
            expr_text = expr_text.replace("^", "**")

            result = sp.integrate(parse_expr(expr_text, transformations=standard_transformations + (implicit_multiplication_application,)), x)

            return {
                "type": "integral",
                "ok": True,
                "expression": expr_text.replace("**", "^"),
                "variable": "x",
                "result": str(result).replace("**", "^"),
            }

    except Exception:
        return None

    return None

def python_calculation_engine(message: str) -> Dict[str, Any]:
    engines = [
        linear_regression_engine,
        statistics_engine,
        finance_engine,
        physics_engine,
        engineering_engine,
        algebra_engine,
        calculus_engine,
        expression_engine,
    ]

    for engine in engines:
        result = engine(message)
        if result is not None:
            return result

    return {
        "type": "calculation_required",
        "ok": False,
        "error": "Lumora detected a calculation-heavy question, but this exact calculation pattern is not automated yet.",
        "suggestion": "Use structured values such as x: 1,2,3 y: 4,5,6, or ask a direct formula question.",
    }


def format_calculation_context(calculation: Dict[str, Any]) -> str:
    return (
        "Python Calculation Engine Result - Source of Truth\n"
        "The assistant must trust these computed values and explain them. "
        "Do not redo arithmetic manually unless only explaining the formula.\n\n"
        + json.dumps(calculation, indent=2)
    )


def calculation_failure_reply(calculation: Dict[str, Any]) -> str:
    return (
        "Python detected that this question needs calculation, but it could not safely parse the values.\n\n"
        f"Reason: {calculation.get('error', 'Unknown parsing error')}\n\n"
        f"Try this format:\n{calculation.get('example') or calculation.get('suggestion') or 'calculate 5*8+2'}"
    )


def deterministic_calculation_reply(calculation: Dict[str, Any]) -> str:
    """
    This is the important fix.
    For successful Python calculations, build the final answer here.
    Do not ask Groq/HF to rewrite arithmetic, because LLMs can introduce wrong values.
    """
    if not calculation.get("ok"):
        return calculation_failure_reply(calculation)

    ctype = calculation.get("type", "")

    if ctype == "linear_regression":
        slope = float(calculation["slope"])
        intercept = float(calculation["intercept"])

        lines = [
            "Linear regression result",
            "",
            "Using the least-squares line:",
            "",
            "\\[ y = mx + b \\]",
            "",
            f"\\[ m = {fmt_num(slope, 12)} \\]",
            f"\\[ b = {fmt_num(intercept, 12)} \\]",
            "",
            "So the fitted equation is:",
            "",
            f"\\[ y = {fmt_num(slope, 6)}x + {fmt_num(intercept, 6)} \\]",
            "",
            "Model quality:",
            f"- \\( R^2 = {fmt_num(calculation.get('r2'), 6)} \\)",
            f"- RMSE = {fmt_num(calculation.get('rmse'), 6)}",
            f"- MAE = {fmt_num(calculation.get('mae'), 6)}",
        ]

        requested = calculation.get("predictions_requested") or {}
        if requested:
            lines.append("")
            lines.append("Prediction:")
            for x_value, y_value in requested.items():
                y_float = float(y_value)
                lines.append("")
                lines.append(f"For \\( x = {x_value} \\):")
                lines.append("")
                lines.append(
                    f"\\[ y = ({fmt_num(slope, 12)} \\times {x_value}) + {fmt_num(intercept, 12)} = {fmt_num(y_float, 12)} \\]"
                )
                lines.append("")
                lines.append(f"Final answer: \\( y \\approx {fmt_num(y_float, 2)} \\)")

        return "\n".join(lines).strip()

    if ctype == "statistics":
        lines = [
            "Statistics result",
            "",
            f"- Count: {calculation.get('count')}",
            f"- Mean: {fmt_num(calculation.get('mean'), 6)}",
            f"- Median: {fmt_num(calculation.get('median'), 6)}",
            f"- Min: {fmt_num(calculation.get('min'), 6)}",
            f"- Max: {fmt_num(calculation.get('max'), 6)}",
            f"- Range: {fmt_num(calculation.get('range'), 6)}",
        ]

        if "sample_variance" in calculation:
            lines.extend([
                f"- Sample variance: {fmt_num(calculation.get('sample_variance'), 6)}",
                f"- Sample standard deviation: {fmt_num(calculation.get('sample_standard_deviation'), 6)}",
                f"- Population variance: {fmt_num(calculation.get('population_variance'), 6)}",
                f"- Population standard deviation: {fmt_num(calculation.get('population_standard_deviation'), 6)}",
            ])

        return "\n".join(lines)

    if ctype == "compound_interest":
        amount = calculation.get("future_value")
        interest = calculation.get("interest_earned")
        return (
            "Compound interest result\n\n"
            "\\[ A = P\\left(1 + \\frac{r}{n}\\right)^{nt} \\]\n\n"
            f"- Principal: {fmt_num(calculation.get('principal'), 2)}\n"
            f"- Annual rate: {fmt_num(float(calculation.get('annual_rate_decimal', 0)) * 100, 4)}%\n"
            f"- Years: {fmt_num(calculation.get('years'), 2)}\n"
            f"- Compounds per year: {fmt_num(calculation.get('compounds_per_year'), 0)}\n"
            f"- Future value: {fmt_num(amount, 2)}\n"
            f"- Interest earned: {fmt_num(interest, 2)}"
        )

    if ctype == "physics_force":
        force_value = fmt_num(calculation.get("force"), 6)
        return (
            "Force result\n\n"
            "\\[ F = ma \\]\n\n"
            f"\\[ F = {fmt_num(calculation.get('mass'), 6)} \\times {fmt_num(calculation.get('acceleration'), 6)} = {force_value}\\,\\text{{N}} \\]\n\n"
            f"Final answer: \\( F = {force_value}\\,\\text{{N}} \\)"
        )

    if ctype == "kinetic_energy":
        return (
            "Kinetic energy result\n\n"
            "\\[ KE = \\frac{1}{2}mv^2 \\]\n\n"
            f"\\[ KE = \\frac{{1}}{{2}}({fmt_num(calculation.get('mass'), 6)})({fmt_num(calculation.get('velocity'), 6)})^2 = {fmt_num(calculation.get('kinetic_energy'), 6)} \\]\n\n"
            f"Final answer: \\( KE = {fmt_num(calculation.get('kinetic_energy'), 6)} \\)"
        )

    if ctype == "ohms_law":
        return (
            "Ohm's Law result\n\n"
            "\\[ V = IR \\]\n\n"
            f"\\[ V = {fmt_num(calculation.get('current'), 6)} \\times {fmt_num(calculation.get('resistance'), 6)} = {fmt_num(calculation.get('voltage'), 6)} \\]\n\n"
            f"Final answer: \\( V = {fmt_num(calculation.get('voltage'), 6)} \\)"
        )

    if ctype == "stress":
        return (
            "Stress result\n\n"
            "\\[ \\text{stress} = \\frac{F}{A} \\]\n\n"
            f"\\[ \\text{{stress}} = \\frac{{{fmt_num(calculation.get('force'), 6)}}}{{{fmt_num(calculation.get('area'), 6)}}} = {fmt_num(calculation.get('stress'), 6)} \\]\n\n"
            f"Final answer: \\( {fmt_num(calculation.get('stress'), 6)} \\)"
        )

    if ctype == "expression":
        return (
            "Calculation result\n\n"
            f"Expression: \\( {calculation.get('expression')} \\)\n\n"
            f"Final answer: \\( {fmt_num(calculation.get('result'), 12)} \\)"
        )

    if ctype == "algebra_solve":
        solutions = calculation.get("solutions", [])
        return (
            "Equation solution\n\n"
            f"Equation: \\( {calculation.get('equation')} \\)\n\n"
            f"Solution(s): {', '.join(str(s) for s in solutions)}"
        )

    if ctype == "derivative":
        return (
            "Derivative result\n\n"
            f"Expression: \\( {calculation.get('expression')} \\)\n\n"
            f"\\[ \\frac{{d}}{{dx}}({calculation.get('expression')}) = {calculation.get('result')} \\]"
        )

    if ctype == "integral":
        return (
            "Integral result\n\n"
            f"Expression: \\( {calculation.get('expression')} \\)\n\n"
            f"\\[ \\int {calculation.get('expression')}\\,dx = {calculation.get('result')} + C \\]"
        )

    return (
        "Calculation result\n\n"
        + json.dumps(calculation, indent=2)
    )


# =============================================================================
# TASK DETECTION
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
    return any(k in lower for k in ["code", "python", "fastapi", "flutter", "dart", "sql", "debug", "error", "main.py", "powershell"])


def is_math_request(message: str) -> bool:
    return needs_python_calculation(message)


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
- Your style should feel close to ChatGPT: helpful, structured, conversational, and careful.

Current time context:
{now_context()}

Core rules:
1. Be clear, helpful, direct, and student-friendly.
2. Never start with "Certainly", "Sure", or "Of course".
3. Avoid excessive markdown.
4. Do not invent sources, URLs, current facts, laws, prices, or news.
5. If web search context is provided, use it for current information.
6. If the user asks for complete code, provide complete working code.
7. If math/calculation is involved, Python calculation_result is the source of truth.
8. If Python calculation_result has ok=True, explain those exact values only.
9. If Python calculation_result has ok=False, do not solve manually or invent numbers; ask the user for clearer values.
10. For math, use LaTeX format:
   - Inline math must use \\( ... \\)
   - Display math must use \\[ ... \\]
   - Fractions must use \\frac{{a}}{{b}}
   - Powers must use x^2 or x^{{n}}
11. Never reveal or ask the user to paste private API keys publicly.
12. Match the user's educational level when provided.
13. Stay on the user's exact subject.
14. Stay on the user's exact task type.
15. Do not mix unrelated topics in the same response.
16. If the user asks for a study explanation, teach the subject; do not call it a calculation unless numbers/formulas are explicitly requested.
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
        "math": "Math mode: show steps clearly and use LaTeX for all formulas.",
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

    if is_math_request(message):
        return """
The user wants math/statistics help.

Rules:
- Use LaTeX for every formula.
- Inline math must use \\( ... \\).
- Display math must use \\[ ... \\].
- Show steps clearly.
- Python calculation_result is the source of truth.
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



def format_quiz_object_response(raw_text: str) -> Optional[str]:
    """
    Converts raw quiz dict/JSON text into a clean student-friendly quiz.

    Handles:
    {'quiz': [{'question': ..., 'options': [...], 'correct': ...}]}
    {"quiz": [{"question": ..., "options": [...], "correct": ...}]}
    {"questions": [...]}
    """
    raw = normalize_text(raw_text)
    if not raw:
        return None

    lower = raw.lower()
    if "'quiz'" not in lower and '"quiz"' not in lower and '"questions"' not in lower and "'questions'" not in lower:
        return None

    candidate = raw.strip()
    candidate = candidate.replace("```json", "").replace("```python", "").replace("```", "").strip()

    # Extract only the object portion if the model added prose around it.
    if "{" in candidate and "}" in candidate:
        candidate = candidate[candidate.find("{"):candidate.rfind("}") + 1]

    data = None

    try:
        data = json.loads(candidate)
    except Exception:
        try:
            data = ast.literal_eval(candidate)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    quiz_items = data.get("quiz") or data.get("questions") or data.get("items")
    if not isinstance(quiz_items, list) or not quiz_items:
        return None

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lines: List[str] = ["Quiz", ""]

    for idx, item in enumerate(quiz_items, start=1):
        if not isinstance(item, dict):
            continue

        question = normalize_text(
            item.get("question")
            or item.get("prompt")
            or item.get("q")
            or ""
        )

        if not question:
            continue

        options = item.get("options") or item.get("choices") or item.get("answers") or []
        correct = normalize_text(
            item.get("correct")
            or item.get("correct_answer")
            or item.get("answer")
            or ""
        )
        explanation = normalize_text(item.get("explanation") or item.get("why") or "")

        lines.append(f"{idx}. {question}")

        option_labels: Dict[str, str] = {}

        if isinstance(options, dict):
            for key, value in options.items():
                label = normalize_text(key).upper().replace(")", "").replace(".", "")
                value_text = normalize_text(value)
                if label and value_text:
                    option_labels[label] = value_text
                    lines.append(f"{label}) {value_text}")

        elif isinstance(options, list):
            for opt_index, value in enumerate(options):
                if opt_index >= len(letters):
                    break
                label = letters[opt_index]
                value_text = normalize_text(value)
                option_labels[label] = value_text
                lines.append(f"{label}) {value_text}")

        correct_label = ""
        correct_text = correct

        if correct:
            clean_correct = correct.strip()
            clean_correct_label = clean_correct.upper().replace(")", "").replace(".", "")

            if clean_correct_label in option_labels:
                correct_label = clean_correct_label
                correct_text = option_labels[correct_label]
            else:
                for label, value in option_labels.items():
                    if clean_correct.lower() == value.lower():
                        correct_label = label
                        correct_text = value
                        break

        if correct_text:
            if correct_label:
                lines.append("")
                lines.append(f"Correct answer: {correct_label}) {correct_text}")
            else:
                lines.append("")
                lines.append(f"Correct answer: {correct_text}")

        if explanation:
            lines.append(f"Explanation: {explanation}")

        lines.append("")

    formatted = "\n".join(lines).strip()
    return formatted if formatted != "Quiz" else None




def repair_group2_chemistry_quiz_facts(reply: str) -> str:
    """
    Local chemistry fact repair for Group 2 quizzes.
    Prevents common wrong answer keys before the user sees them.
    """
    s = normalize_text(reply)

    lower = s.lower()
    if "group 2" not in lower and "alkaline earth" not in lower:
        return s

    # Group 2 reactivity trend:
    # Reactivity generally increases down the group.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+What is the trend in the reactivity of Group 2 elements\?\s*'
        r'\nA\)\s+Increases down the group\s*'
        r'\nB\)\s+Decreases down the group\s*'
        r'\nC\)\s+Remains the same down the group\s*'
        r'\nD\)\s+Increases up the group\s*'
        r'\n\s*Correct answer:\s+B\)\s+Decreases down the group',
        r'\1. What is the trend in the reactivity of Group 2 elements?\n'
        r'A) Increases down the group\n'
        r'B) Decreases down the group\n'
        r'C) Remains the same down the group\n'
        r'D) Increases up the group\n\n'
        r'Correct answer: A) Increases down the group',
        s,
    )

    # If a model gives only the wrong answer line in a reactivity block, fix it.
    s = re.sub(
        r'(?ms)(What is the trend in the reactivity of Group 2 elements\?.*?)'
        r'Correct answer:\s+B\)\s+Decreases down the group',
        r'\1Correct answer: A) Increases down the group',
        s,
    )

    # Group 2 melting points do not follow a perfectly simple monotonic trend.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+What is the trend in the melting points of Group 2 elements\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which statement best describes the melting point trend of Group 2 elements?\n'
        r'A) They follow a simple steady increase down the group\n'
        r'B) They follow a simple steady decrease down the group\n'
        r'C) They vary and do not follow a perfectly regular trend\n'
        r'D) They are all the same\n\n'
        r'Correct answer: C) They vary and do not follow a perfectly regular trend',
        s,
    )

    # Fireworks color facts.
    # Barium = green, Strontium = red, Magnesium = bright white light/sparks.
    s = re.sub(
        r'(?ms)^(\d+)\.\s+Which Group 2 element is used in fireworks to produce a bright green color\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which Group 2 element is used in fireworks to produce a bright green color?\n'
        r'A) Magnesium (Mg)\n'
        r'B) Calcium (Ca)\n'
        r'C) Strontium (Sr)\n'
        r'D) Barium (Ba)\n\n'
        r'Correct answer: D) Barium (Ba)',
        s,
    )

    s = re.sub(
        r'(?ms)^(\d+)\.\s+Which Group 2 element is used in fireworks to produce a red color\?.*?'
        r'Correct answer:\s+[A-D]\).*?(?=\n\n\d+\.|\Z)',
        r'\1. Which Group 2 element is used in fireworks to produce a red color?\n'
        r'A) Magnesium (Mg)\n'
        r'B) Calcium (Ca)\n'
        r'C) Strontium (Sr)\n'
        r'D) Barium (Ba)\n\n'
        r'Correct answer: C) Strontium (Sr)',
        s,
    )

    return s.strip()




def normalize_quiz_output_text(reply: str) -> str:
    """
    Universal quiz cleanup.
    Fixes formatting problems for all subjects, not only chemistry.

    Fixes:
    - A) A) Option -> A) Option
    - Correct answer: B) B) Option -> Correct answer: B) Option
    - Markdown bold in questions
    - Extra spacing
    """
    s = normalize_text(reply)

    if not s:
        return s

    # Remove markdown bold markers.
    s = re.sub(r'\*\*(.*?)\*\*', r'\1', s)

    # Fix duplicated option labels:
    # A) A) Group 1 -> A) Group 1
    s = re.sub(
        r'(?m)^([A-D])\)\s+\1\)\s+',
        r'\1) ',
        s,
        flags=re.IGNORECASE,
    )

    # Fix duplicated correct answer labels:
    # Correct answer: B) B) Group 2 -> Correct answer: B) Group 2
    s = re.sub(
        r'(?im)^(Correct answer:\s*)([A-D])\)\s+\2\)\s+',
        r'\1\2) ',
        s,
    )

    # Fix "Correct answer: B) B)" even with lowercase/spaces.
    s = re.sub(
        r'(?im)^(Correct answer:\s*)([A-D])\)\s+([A-D])\)\s+',
        lambda m: f"{m.group(1)}{m.group(2).upper()}) " if m.group(2).upper() == m.group(3).upper() else m.group(0),
        s,
    )

    # Normalize common LaTeX dollars in quiz text to display-friendly \( ... \)
    # This helps frontend math renderer.
    s = re.sub(r'\$([^$\n]+)\$', r'\\( \1 \\)', s)

    # Ensure every numbered question starts on a clean line.
    s = re.sub(r'(?<!\n)\s+(\d+\.\s+)', r'\n\n\1', s)

    # Ensure Correct answer has a blank line before next question.
    s = re.sub(r'(?m)^(Correct answer:.*?)(\n)(\d+\.\s+)', r'\1\n\n\3', s)

    # Remove too many blank lines.
    s = re.sub(r'\n{3,}', '\n\n', s)

    return s.strip()


def verifier_improvement_was_not_applied(original: str, improved: str, issues: List[str]) -> bool:
    if not issues:
        return False

    o = re.sub(r'\s+', ' ', normalize_text(original)).strip().lower()
    i = re.sub(r'\s+', ' ', normalize_text(improved)).strip().lower()

    return o == i



def clean_response_text(text: str) -> str:
    if not text:
        return ""

    quiz_formatted = format_quiz_object_response(str(text))
    if quiz_formatted:
        return normalize_quiz_output_text(repair_group2_chemistry_quiz_facts(quiz_formatted))

    cleaned = str(text)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }

    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)

    # Fix common UTF-8 mojibake from model/provider output.
    mojibake_replacements = {
        "Â²âº": "^2+",
        "Â²â»": "^2-",
        "Â³âº": "^3+",
        "Â³â»": "^3-",
        "Âº": "+",
        "Â»": "-",
        "âº": "+",
        "â»": "-",
        "Â²": "^2",
        "Â³": "^3",
        "²": "^2",
        "³": "^3",
        "⁺": "+",
        "⁻": "-",
        "₂": "2",
        "₃": "3",
        "Oâ": "O",
        "CaÂ": "Ca",
        "MgÂ": "Mg",
        "BaÂ": "Ba",
        "SrÂ": "Sr",
        "Â": "",
    }

    for bad, good in mojibake_replacements.items():
        cleaned = cleaned.replace(bad, good)

    cleaned = re.sub(r"(?i)^\s*(certainly|sure|of course)[,!\.\s-]*", "", cleaned).strip()
    cleaned = re.sub(r"\n{4,}", "\n\n", cleaned)
    return normalize_quiz_output_text(repair_group2_chemistry_quiz_facts(cleaned.strip()))


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


def call_groq_model(
    model_name: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    try:
        client = get_groq_client()
        started = time.time()
        temp = DEFAULT_TEMPERATURE if temperature is None else temperature

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
                timeout=GROQ_TIMEOUT_SECONDS,
            )
        except TypeError:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temp,
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
    calculation_result: Optional[Dict[str, Any]] = None,
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

    if calculation_result is not None:
        messages.append(
            {
                "role": "system",
                "content": format_calculation_context(calculation_result),
            }
        )

    messages.extend(limit_history(history, max_items=3 if fast else MAX_HISTORY_ITEMS))
    messages.append({"role": "user", "content": message})

    return messages, used_search


# =============================================================================
# LUMORA BRAIN
# =============================================================================

def brain_classify_task(message: str) -> str:
    text = message.lower()

    # Current/latest questions need search first.
    if should_search_internet(text):
        return "search"

    # Explicit task types should win before math.
    if is_code_request(text):
        return "code"
    if is_quiz_request(text):
        return "quiz"
    if is_flashcard_request(text):
        return "cards"
    if is_study_plan_request(text):
        return "study"
    if is_research_request(text):
        return "research"
    if is_image_request(text):
        return "image"
    if is_video_request(text):
        return "video"

    # Only explicit numeric/computational tasks go to Python math.
    if is_math_request(text):
        return "math"

    # Default for Lumora: universal study tutor.
    if is_conceptual_study_request(message):
        return "study"

    if len(text) < 200:
        return "study"

    return "reasoning"

def brain_choose_mode(task_type: str, original_mode: str) -> str:
    if original_mode and original_mode != "study":
        return original_mode

    mapping = {
        "simple": "chat",
        "reasoning": "general",
        "search": "research",
        "code": "code",
        "math": "math",
        "research": "research",
        "quiz": "quiz",
        "cards": "cards",
        "study": "study",
        "image": "image",
        "video": "video",
    }
    return mapping.get(task_type, "general")


def brain_choose_max_tokens(task_type: str, fast: bool, long_answer: bool) -> int:
    if fast or task_type == "simple":
        return FAST_MAX_TOKENS
    if long_answer or task_type in {"research", "code", "math", "reasoning"}:
        return LONG_MAX_TOKENS
    return DEFAULT_MAX_TOKENS


def brain_model_plan(task_type: str, fast: bool) -> List[Tuple[str, str]]:
    plan: List[Tuple[str, str]] = []

    def add(provider: str, model: str) -> None:
        model = normalize_text(model)
        if model and (provider, model) not in plan:
            plan.append((provider, model))

    if AI_PROVIDER in {"auto", "groq"}:
        if fast or task_type == "simple":
            add("groq", GROQ_FAST_MODEL)
            add("groq", GROQ_MODEL)
            add("groq", GROQ_BACKUP_MODEL)
        elif task_type in {"code", "math", "research", "reasoning", "search"}:
            add("groq", GROQ_MODEL)
            add("groq", GROQ_BACKUP_MODEL)
            add("groq", GROQ_FAST_MODEL)
        else:
            add("groq", GROQ_FAST_MODEL)
            add("groq", GROQ_MODEL)
            add("groq", GROQ_BACKUP_MODEL)

    if AI_PROVIDER in {"auto", "hf", "huggingface"}:
        add("huggingface", HF_MODEL)
        add("huggingface", HF_BACKUP_MODEL)
        add("huggingface", HF_THIRD_MODEL)

    return plan


def brain_generate_answer(
    messages: List[Dict[str, str]],
    task_type: str,
    fast: bool,
    max_tokens: int,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []

    for provider, model_name in brain_model_plan(task_type, fast):
        if provider == "groq":
            result = call_groq_model(model_name, messages, max_tokens=max_tokens)
        else:
            result = call_hf_text_model(model_name, messages, max_tokens=max_tokens)

        if result.get("ok") and normalize_text(result.get("reply", "")):
            return result, errors

        errors.append(f"{provider}:{model_name}: {result.get('error', 'empty reply')}")

    return None, errors


def local_study_safety_repair(question: str, answer: str, task_type: str) -> Tuple[str, List[str]]:
    """
    Local backup repair when the verifier returns non-JSON.
    This does not replace the AI verifier; it catches common study-answer issues.
    """
    repaired = clean_response_text(answer)
    issues: List[str] = []

    combined = f"{question}\n{repaired}".lower()

    # Fix common chemistry explanation issue for Mg + O2 -> MgO.
    if "group 2" in combined and "mgo" in combined:
        old1 = "Oxygen (O2) gains 2 electrons to form a -2 ion (O2-)."
        new1 = "Each oxygen atom gains 2 electrons to form an oxide ion, \\( O^{2-} \\). Since \\( O_2 \\) contains two oxygen atoms, the oxygen molecule gains 4 electrons in total and forms two oxide ions."
        if old1 in repaired:
            repaired = repaired.replace(old1, new1)
            issues.append("Corrected oxide ion explanation for oxygen molecule.")

        old2 = "The +2 ion (Mg2+) and the -2 ion (O2-) combine to form a neutral compound, magnesium oxide (MgO)."
        new2 = "\\( Mg^{2+} \\) ions and \\( O^{2-} \\) oxide ions combine in a 1:1 ratio to form neutral magnesium oxide, \\( MgO \\)."
        if old2 in repaired:
            repaired = repaired.replace(old2, new2)
            issues.append("Corrected MgO ionic explanation.")

        repaired = repaired.replace("Mg2+", "\\( Mg^{2+} \\)")
        repaired = repaired.replace("O2-", "\\( O^{2-} \\)")
        repaired = repaired.replace("O2)", "\\( O_2 \\))")
        repaired = repaired.replace("(O2)", "\\( O_2 \\)")

    return repaired, issues


def brain_verifier(question: str, answer: str, task_type: str) -> Dict[str, Any]:
    if not BRAIN_VERIFY:
        return {
            "approved": True,
            "score": 100,
            "issues": [],
            "improved_answer": answer,
            "verifier": "disabled",
        }

    if not GROQ_API_KEY:
        repaired, local_issues = local_study_safety_repair(question, answer, task_type)
        return {
            "approved": True,
            "score": 80 if local_issues else 75,
            "issues": ["Verifier skipped because GROQ_API_KEY is missing."] + local_issues,
            "improved_answer": normalize_quiz_output_text(repaired),
            "verifier": "local_fallback_no_groq",
        }

    verify_prompt = f"""
You are Lumora Brain Verifier.

Return ONLY valid JSON. No markdown. No code fences. No explanation outside JSON.

Check this draft answer before the user sees it.

Check for:
- correctness
- clarity
- missing steps
- hallucinations
- unsupported claims
- subject lock: answer only the user's requested subject
- task lock: do not mix quiz, research, coding, and study formats unless requested
- quiz quality: every multiple-choice question must have exactly one best correct answer
- quiz quality: do not output duplicated labels such as A) A) or Correct answer: B) B)
- quiz quality: if an option is ambiguous, replace the whole question with a safer verified question
- quiz quality: avoid obscure application questions unless the user requested advanced level
- quiz quality: avoid ambiguous questions
- quiz quality: avoid two options that mean the same correct answer
- quiz quality: answer keys must match the options exactly
- quiz quality: if facts are uncertain, rewrite the question to a safer verified concept
- quiz quality: format as numbered questions with A), B), C), D), then Correct answer
- quiz quality: if you list an issue, improved_answer must be different from the draft and must fix the issue
- quiz quality: avoid ambiguous science questions where more than one option could be partly correct
- quiz quality: for “loss of electrons,” the process is oxidation
- quiz quality: avoid vague application questions like “used in antacids” unless the compound is specified
- science accuracy: formulas, units, symbols, balanced equations, charges, ions, and terminology
- chemistry accuracy: balanced equations, oxidation states, ion charges, and periodic trends
- Group 2 rule: reactivity increases down the group
- Group 2 rule: elements usually form +2 ions and have outer configuration ns^2
- Group 2 rule: Group 2 oxides are generally basic
- Group 2 rule: barium gives green fireworks, strontium gives red, magnesium gives bright white light/sparks
- Group 2 rule: melting points do not follow a perfectly regular simple trend
- no broken characters such as CaÂ²âº, Oâ, âº, or â»

Important chemistry rule:
- For MgO, magnesium forms Mg^2+ and oxygen forms O^2-.
- Oxygen gas is O2. One O2 molecule forms two O^2- oxide ions, so it gains 4 electrons total.
- Correct balanced example: 2Mg + O2 -> 2MgO.
- Correct balanced example: Mg + 2H2O -> Mg(OH)2 + H2.

Important math rule:
If the answer contains math, improved_answer must use LaTeX:
- inline math: \\( ... \\)
- display math: \\[ ... \\]
- fractions: \\frac{{a}}{{b}}

Task type: {task_type}

User question:
{question}

Draft answer:
{answer}

Required JSON schema:
{{
  "approved": true,
  "score": 0,
  "issues": [],
  "improved_answer": ""
}}

Rules:
- score must be 0 to 100.
- approved should be true only if score is at least {BRAIN_MIN_VERIFY_SCORE} AND all listed issues are fixed in improved_answer. For quizzes, if there are any factual, ambiguity, duplicate-label, or answer-key issues, improved_answer must rewrite the affected questions.
- improved_answer must contain the final user-facing answer. If you list any issue, improved_answer MUST fix that issue and must not be identical to the draft answer.
- Return JSON only.
"""

    messages = [
        {
            "role": "system",
            "content": "You are a strict verifier. You must return one valid JSON object only.",
        },
        {"role": "user", "content": verify_prompt},
    ]

    try:
        client = get_groq_client()
        try:
            response = client.chat.completions.create(
                model=GROQ_VERIFIER_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=VERIFIER_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
        except TypeError:
            response = client.chat.completions.create(
                model=GROQ_VERIFIER_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=VERIFIER_MAX_TOKENS,
            )

        raw_reply = response.choices[0].message.content or ""
        data = extract_json_object(raw_reply)

    except Exception as e:
        repaired, local_issues = local_study_safety_repair(question, answer, task_type)
        return {
            "approved": True,
            "score": 80 if local_issues else 75,
            "issues": [f"Verifier unavailable: {e}"] + local_issues,
            "improved_answer": normalize_quiz_output_text(repaired),
            "verifier": "local_fallback_error",
            "verifier_model": None,
        }

    if not data:
        repaired, local_issues = local_study_safety_repair(question, answer, task_type)
        return {
            "approved": True,
            "score": 80 if local_issues else 70,
            "issues": ["Verifier returned non-JSON; local safety repair applied."] + local_issues,
            "improved_answer": normalize_quiz_output_text(repaired),
            "verifier": "local_fallback_non_json",
            "verifier_model": GROQ_VERIFIER_MODEL,
        }

    score = clamp_int(data.get("score", 75), 75, 0, 100)
    improved = normalize_quiz_output_text(normalize_text(data.get("improved_answer", "")) or answer)
    improved, local_issues = local_study_safety_repair(question, improved, task_type)

    issues = data.get("issues", [])
    if not isinstance(issues, list):
        issues = [str(issues)]
    issues.extend(local_issues)

    return {
        "approved": bool(data.get("approved", score >= BRAIN_MIN_VERIFY_SCORE)),
        "score": score,
        "issues": issues,
        "improved_answer": improved,
        "verifier": "groq_json",
        "verifier_model": GROQ_VERIFIER_MODEL,
    }


def repair_unapproved_quiz_with_ai(question: str, draft_answer: str, verification: Dict[str, Any]) -> Optional[str]:
    """
    Universal quiz repair pass for any subject.
    Runs when verifier rejects a quiz.
    """
    if not GROQ_API_KEY:
        return None

    issues = verification.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]

    issues_text = "\n".join(f"- {normalize_text(str(x))}" for x in issues)

    repair_prompt = f"""
You are Lumora Quiz Repair.

The verifier rejected this quiz. Rewrite it before the student sees it.

Rules:
- Works for any subject.
- Return only the repaired quiz text.
- Do not return JSON.
- Every multiple-choice question must have exactly one best answer.
- Use A), B), C), D) options.
- Include "Correct answer: X) option text" after every question.
- Fix every verifier issue.
- Avoid ambiguous questions.
- Avoid duplicated labels like A) A).
- Avoid "all of the above" and "both A and C".
- If a question is unclear, replace the entire question with a safer verified one.
- If asking about loss of electrons, the process is oxidation.
- If asking about oxygen released in photosynthesis, oxygen comes from water during light-dependent reactions.

Verifier issues:
{issues_text}

User request:
{question}

Rejected quiz:
{draft_answer}
"""

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_VERIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You repair quizzes for factual accuracy, clarity, and unambiguous answer keys.",
                },
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0,
            max_tokens=2200,
        )

        repaired = response.choices[0].message.content or ""
        repaired = clean_response_text(repaired)
        repaired = normalize_quiz_output_text(repaired)
        return repaired.strip() if repaired.strip() else None

    except Exception as e:
        print(f"Quiz repair failed: {e}")
        return None



def brain_store_memory(
    user_key: str,
    question: str,
    answer: str,
    task_type: str,
    provider: str,
    model: str,
    verification: Dict[str, Any],
) -> None:
    _LUMORA_BRAIN_MEMORY.append(
        {
            "time": utc_now(),
            "user_hash": hash_text(user_key),
            "question": question[:1000],
            "answer": answer[:2000],
            "task_type": task_type,
            "provider": provider,
            "model": model,
            "verification_score": verification.get("score", 0),
            "verification_approved": verification.get("approved", True),
            "issues": verification.get("issues", []),
        }
    )

    if len(_LUMORA_BRAIN_MEMORY) > BRAIN_MEMORY_MAX_ITEMS:
        overflow = max(50, BRAIN_MEMORY_MAX_ITEMS // 5)
        del _LUMORA_BRAIN_MEMORY[:overflow]



def is_deterministic_linear_regression_lesson_request(message: str) -> bool:
    text = normalize_text(message).lower()

    if "linear regression" not in text:
        return False

    # If the user gives real x/y data, let the Python calculation engine handle it.
    try:
        if parse_regression_pairs(message):
            return False
    except Exception:
        pass

    lesson_words = [
        "explain", "what is", "teach", "simple example", "example",
        "lesson", "understand", "overview", "how does", "in simple terms"
    ]

    return any(word in text for word in lesson_words)


def deterministic_linear_regression_lesson_reply(message: str) -> Optional[str]:
    if not is_deterministic_linear_regression_lesson_request(message):
        return None

    # Verified example:
    # x = bedrooms, y = house price
    # slope = 50000, intercept = 50000
    # model: y = 50000x + 50000
    # prediction for x = 6: y = 350000
    return (
        "Linear regression explained\n\n"
        "Linear regression is a method used to model the relationship between an input variable "
        "\\( x \\) and an output variable \\( y \\). It finds the best straight line that can be used "
        "to predict \\( y \\) from \\( x \\).\n\n"
        "The general equation is:\n\n"
        "\\[ y = mx + b \\]\n\n"
        "Where:\n"
        "- \\( y \\) is the value we want to predict\n"
        "- \\( x \\) is the input value\n"
        "- \\( m \\) is the slope\n"
        "- \\( b \\) is the intercept\n\n"
        "Simple example\n\n"
        "Suppose we want to predict house price from the number of bedrooms:\n\n"
        "| Bedrooms \\(x\\) | Price \\(y\\) |\n"
        "|---:|---:|\n"
        "| 2 | 150,000 |\n"
        "| 3 | 200,000 |\n"
        "| 4 | 250,000 |\n"
        "| 5 | 300,000 |\n\n"
        "Each time the number of bedrooms increases by 1, the price increases by 50,000. "
        "So the slope is:\n\n"
        "\\[ m = 50000 \\]\n\n"
        "Now use one point, for example \\( x = 2, y = 150000 \\), to find the intercept:\n\n"
        "\\[ y = mx + b \\]\n\n"
        "\\[ 150000 = 50000(2) + b \\]\n\n"
        "\\[ 150000 = 100000 + b \\]\n\n"
        "\\[ b = 50000 \\]\n\n"
        "So the correct regression equation is:\n\n"
        "\\[ y = 50000x + 50000 \\]\n\n"
        "Prediction example\n\n"
        "For a 6-bedroom house:\n\n"
        "\\[ y = 50000(6) + 50000 \\]\n\n"
        "\\[ y = 300000 + 50000 = 350000 \\]\n\n"
        "Final answer: the predicted price for a 6-bedroom house is 350,000.\n\n"
        "Key idea: linear regression finds the line that best predicts an output from an input."
    )


def lumora_brain_engine(
    request: Request,
    chat_request: ChatRequest,
    fast: bool = False,
    force_long: bool = False,
) -> Dict[str, Any]:
    check_app_key(request)

    request_id = make_request_id()
    user_key = get_user_key(request, chat_request.user_id)

    rate_limit(user_key=user_key, action="chat", limit=RATE_LIMIT_CHAT_PER_MINUTE, window_seconds=60)

    message = clean_user_message(chat_request.message)
    if not message:
        return {
            "ok": True,
            "reply": "Please type a message first.",
            "brain": "Lumora Brain v12.7.7",
            "request_id": request_id,
        }

    date_reply = current_datetime_reply(message)
    if date_reply:
        track_usage(user_key, "chat", True)
        return {
            "ok": True,
            "reply": date_reply,
            "brain": "Lumora Brain v12.7.7",
            "task_type": "datetime",
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
            "brain": "Lumora Brain v12.7.7",
            "task_type": "quick_reply",
            "provider": "quick_reply",
            "model": "quick-reply",
            "cached": False,
            "request_id": request_id,
        }


    lesson_reply = deterministic_linear_regression_lesson_reply(message)
    if lesson_reply:
        verification = {
            "approved": True,
            "score": 100,
            "issues": [],
            "verifier": "deterministic_lesson_template",
            "verifier_model": None,
        }

        brain_store_memory(
            user_key=user_key,
            question=message,
            answer=lesson_reply,
            task_type="study",
            provider="python",
            model="deterministic-linear-regression-lesson",
            verification=verification,
        )
        track_usage(user_key, "chat", True)

        return {
            "ok": True,
            "reply": lesson_reply,
            "brain": "Lumora Brain v12.7.7",
            "task_type": "study",
            "mode": "study",
            "provider": "python",
            "model": "deterministic-linear-regression-lesson",
            "cached": False,
            "used_search": False,
            "calculation_used": False,
            "calculation_result": None,
            "request_id": request_id,
            "elapsed_seconds": 0.0,
            "verification": verification,
        }

    task_type = brain_classify_task(message)
    mode = brain_choose_mode(task_type, normalize_text(chat_request.mode))
    long_answer = bool(force_long or chat_request.long_answer or task_type in {"research", "code", "math", "reasoning"})

    cached = get_cached_reply(message, mode, fast, long_answer)
    if cached:
        track_usage(user_key, "chat", True)
        return {
            "ok": True,
            "reply": cached,
            "brain": "Lumora Brain v12.7.7",
            "task_type": task_type,
            "mode": mode,
            "provider": "cache",
            "model": "cache",
            "cached": True,
            "used_search": False,
            "request_id": request_id,
        }

    calculation_result: Optional[Dict[str, Any]] = None
    calculation_used = False

    if task_type == "math" or needs_python_calculation(message):
        calculation_result = python_calculation_engine(message)
        calculation_used = True

        # CRITICAL FIX:
        # If Python calculation succeeds, return a deterministic answer immediately.
        # Do not allow Groq/HF to rewrite arithmetic or generate broken Python.
        if calculation_result.get("ok"):
            reply = deterministic_calculation_reply(calculation_result)
            reply = clean_response_text(reply)

            verification = {
                "approved": True,
                "score": 100,
                "issues": [],
                "verifier": "python_calculation_engine",
                "verifier_model": None,
            }

            set_cached_reply(message, mode, fast, long_answer, reply)
            brain_store_memory(
                user_key=user_key,
                question=message,
                answer=reply,
                task_type=task_type,
                provider="python",
                model="deterministic-calculation-reply",
                verification=verification,
            )
            track_usage(user_key, "chat", True)

            return {
                "ok": True,
                "reply": reply,
                "brain": "Lumora Brain v12.7.7",
                "task_type": task_type,
                "mode": mode,
                "provider": "python",
                "model": "deterministic-calculation-reply",
                "cached": False,
                "used_search": False,
                "calculation_used": True,
                "calculation_result": calculation_result,
                "request_id": request_id,
                "elapsed_seconds": 0.0,
                "verification": verification,
            }

        if calculation_result.get("ok") is False and calculation_result.get("type") != "calculation_required":
            reply = calculation_failure_reply(calculation_result)
            track_usage(user_key, "chat", True)
            return {
                "ok": True,
                "reply": reply,
                "brain": "Lumora Brain v12.7.7",
                "task_type": task_type,
                "mode": mode,
                "provider": "python",
                "model": "calculation-parser",
                "cached": False,
                "used_search": False,
                "calculation_used": True,
                "calculation_result": calculation_result,
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
        calculation_result=calculation_result,
    )

    max_tokens = brain_choose_max_tokens(task_type, fast, long_answer)
    result, errors = brain_generate_answer(messages, task_type, fast, max_tokens)

    if not result:
        track_usage(user_key, "chat", False)
        return {
            "ok": False,
            "reply": "Lumora could not get a response from the configured AI providers. Check GROQ_API_KEY or HF_TOKEN in your .env file.",
            "brain": "Lumora Brain v12.7.7",
            "task_type": task_type,
            "mode": mode,
            "provider": None,
            "model": None,
            "cached": False,
            "used_search": used_search,
            "errors": errors[-5:],
            "calculation_used": calculation_used,
            "calculation_result": calculation_result,
            "request_id": request_id,
        }

    draft_reply = clean_response_text(result.get("reply", ""))

    verification = {"approved": True, "score": 100, "issues": [], "verifier": "skipped"}

    should_verify = chat_request.verify if chat_request.verify is not None else BRAIN_VERIFY
    if should_verify and task_type in {"study", "quiz", "cards", "research", "code", "reasoning", "search", "simple"}:
        verification = brain_verifier(message, draft_reply, task_type)

        # FINAL_QUIZ_REPAIR_GATE_V1277
        if task_type == "quiz" and verification and not verification.get("approved", True):
            repaired_quiz = repair_unapproved_quiz_with_ai(message, reply, verification)
            if repaired_quiz:
                reply = repaired_quiz
                verification = brain_verifier(message, reply, task_type)
                improved_after_repair = verification.get("improved_answer") if verification else None
                if improved_after_repair:
                    reply = normalize_quiz_output_text(improved_after_repair)
        
            # Final safety: do not show a rejected quiz to students.
            if verification and not verification.get("approved", True):
                safe_quiz_message = (
                    "I generated a quiz, but the verifier found accuracy or clarity issues, "
                    "so I did not show it. Please try again, or ask for a simpler quiz."
                )
                reply = safe_quiz_message
                verification["improved_answer"] = safe_quiz_message
        final_reply = clean_response_text(verification.get("improved_answer") or draft_reply)
    else:
        final_reply = draft_reply

    set_cached_reply(message, mode, fast, long_answer, final_reply)

    brain_store_memory(
        user_key=user_key,
        question=message,
        answer=final_reply,
        task_type=task_type,
        provider=result.get("provider", ""),
        model=result.get("model", ""),
        verification=verification,
    )

    track_usage(user_key, "chat", True)

    return {
        "ok": True,
        "reply": final_reply,
        "brain": "Lumora Brain v12.7.7",
        "task_type": task_type,
        "mode": mode,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "cached": False,
        "used_search": used_search,
        "calculation_used": calculation_used,
        "calculation_result": calculation_result,
        "request_id": request_id,
        "elapsed_seconds": result.get("elapsed_seconds"),
        "verification": verification,
    }


# =============================================================================
# IMAGE AND VIDEO
# =============================================================================

def hf_inference_post(model_name: str, payload: Dict[str, Any], timeout: int) -> Tuple[bool, Any, str]:
    if not HF_TOKEN:
        return False, None, "HF_TOKEN is missing."

    url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Accept": "application/json, image/png, video/mp4, application/octet-stream",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        if response.status_code >= 400:
            return False, None, f"HF inference status {response.status_code}: {response.text[:800]}"

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return True, response.json(), ""

        return True, {
            "bytes": response.content,
            "content_type": content_type or "application/octet-stream",
        }, ""

    except requests.exceptions.Timeout:
        return False, None, "HF inference timed out."
    except Exception as e:
        return False, None, str(e)


@app.get("/image-health")
def image_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "image_model": HF_IMAGE_MODEL,
        "hf_token_set": bool(HF_TOKEN),
        "pillow_available": Image is not None,
    }


@app.get("/video-health")
def video_health() -> Dict[str, Any]:
    return {
        "ok": True,
        "video_model": HF_VIDEO_MODEL,
        "video_provider": HF_VIDEO_PROVIDER,
        "hf_token_set": bool(HF_TOKEN),
        "status": "experimental",
    }


@app.post("/image")
def image_endpoint(payload: ImageRequest, request: Request) -> Dict[str, Any]:
    check_app_key(request)
    user_key = get_user_key(request)
    rate_limit(user_key, "image", RATE_LIMIT_IMAGE_PER_HOUR, 3600)

    prompt = clean_user_message(payload.prompt, MAX_PROMPT_CHARS_IMAGE)
    style = clean_user_message(payload.style, 500)
    negative = clean_user_message(payload.negative_prompt, 800)

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    full_prompt = f"{prompt}. Style: {style}".strip()
    data_payload = {
        "inputs": full_prompt,
        "parameters": {
            "negative_prompt": negative,
            "width": clamp_dimension(payload.width),
            "height": clamp_dimension(payload.height),
        },
    }

    ok, data, error = hf_inference_post(HF_IMAGE_MODEL, data_payload, HF_IMAGE_TIMEOUT_SECONDS)
    track_usage(user_key, "image", ok)

    if not ok:
        return {
            "ok": False,
            "error": error,
            "model": HF_IMAGE_MODEL,
            "prompt": full_prompt,
        }

    if isinstance(data, dict) and "bytes" in data:
        raw = data["bytes"]
        content_type = data.get("content_type", "image/png")
        b64 = base64.b64encode(raw).decode("utf-8")
        return {
            "ok": True,
            "model": HF_IMAGE_MODEL,
            "prompt": full_prompt,
            "content_type": content_type,
            "image_base64": b64,
            "data_url": f"data:{content_type};base64,{b64}",
        }

    return {
        "ok": True,
        "model": HF_IMAGE_MODEL,
        "prompt": full_prompt,
        "result": data,
    }


@app.post("/video")
def video_endpoint(payload: VideoRequest, request: Request) -> Dict[str, Any]:
    check_app_key(request)
    user_key = get_user_key(request)
    rate_limit(user_key, "video", RATE_LIMIT_VIDEO_PER_HOUR, 3600)

    prompt = clean_user_message(payload.prompt, MAX_PROMPT_CHARS_VIDEO)
    style = clean_user_message(payload.style, 500)
    negative = clean_user_message(payload.negative_prompt, 800)

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    seconds = clamp_video_seconds(payload.seconds)
    full_prompt = f"{prompt}. Style: {style}. Duration: {seconds} seconds.".strip()

    data_payload = {
        "inputs": full_prompt,
        "parameters": {
            "negative_prompt": negative,
            "num_frames": seconds * 8,
        },
    }

    ok, data, error = hf_inference_post(HF_VIDEO_MODEL, data_payload, HF_VIDEO_TIMEOUT_SECONDS)
    track_usage(user_key, "video", ok)

    if not ok:
        return {
            "ok": False,
            "error": error,
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
            "prompt": full_prompt,
            "note": "Video generation is provider-dependent and may require a model/provider that supports text-to-video through your HF account.",
        }

    if isinstance(data, dict) and "bytes" in data:
        raw = data["bytes"]
        content_type = data.get("content_type", "video/mp4")
        b64 = base64.b64encode(raw).decode("utf-8")
        return {
            "ok": True,
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
            "prompt": full_prompt,
            "content_type": content_type,
            "video_base64": b64,
            "data_url": f"data:{content_type};base64,{b64}",
        }

    return {
        "ok": True,
        "model": HF_VIDEO_MODEL,
        "provider": HF_VIDEO_PROVIDER,
        "prompt": full_prompt,
        "result": data,
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.post("/calculate")
def calculate_endpoint(payload: CalculateRequest, request: Request) -> Dict[str, Any]:
    check_app_key(request)
    message = clean_user_message(payload.message)
    result = python_calculation_engine(message)

    return {
        "ok": bool(result.get("ok")),
        "calculation_used": True,
        "result": result,
        "reply": deterministic_calculation_reply(result),
    }


@app.post("/chat")
def chat_endpoint(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_brain_engine(request, payload, fast=False, force_long=False)


@app.post("/chat-fast")
def chat_fast_endpoint(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_brain_engine(request, payload, fast=True, force_long=False)


@app.post("/chat-long")
def chat_long_endpoint(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_brain_engine(request, payload, fast=False, force_long=True)


@app.post("/brain-chat")
def brain_chat_endpoint(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_brain_engine(request, payload, fast=False, force_long=False)


@app.post("/generate")
def generate_endpoint(payload: ChatRequest, request: Request) -> Dict[str, Any]:
    return lumora_brain_engine(request, payload, fast=False, force_long=payload.long_answer)


@app.post("/study-plan")
def study_plan_endpoint(payload: StudyPlanRequest, request: Request) -> Dict[str, Any]:
    prompt = (
        f"Create a {payload.days}-day study plan for {payload.topic}. "
        f"Level: {payload.level}. Minutes per day: {payload.minutes_per_day}. "
        f"Goal: {payload.goal or 'master the fundamentals and practice effectively'}."
    )
    chat_payload = ChatRequest(message=prompt, mode="study", long_answer=True)
    return lumora_brain_engine(request, chat_payload, fast=False, force_long=True)


@app.post("/quiz-generator")
def quiz_generator_endpoint(payload: QuizRequest, request: Request) -> Dict[str, Any]:
    prompt = (
        f"Create a {payload.questions}-question {payload.question_type} quiz on {payload.topic}. "
        f"Level: {payload.level}. Include correct answers and short explanations. "
        f"Notes: {payload.notes}"
    )
    chat_payload = ChatRequest(message=prompt, mode="quiz", long_answer=True)
    return lumora_brain_engine(request, chat_payload, fast=False, force_long=True)


@app.post("/flashcards")
def flashcards_endpoint(payload: FlashcardRequest, request: Request) -> Dict[str, Any]:
    prompt = (
        f"Create {payload.cards} flashcards on {payload.topic}. "
        f"Level: {payload.level}. Notes: {payload.notes}"
    )
    chat_payload = ChatRequest(message=prompt, mode="cards", long_answer=True)
    return lumora_brain_engine(request, chat_payload, fast=False, force_long=True)


@app.post("/research-helper")
def research_helper_endpoint(payload: ResearchRequest, request: Request) -> Dict[str, Any]:
    prompt = (
        f"Help me research this topic: {payload.topic}. "
        f"Level: {payload.level}. Requirements: {payload.requirements}. "
        "Organize the answer with an outline, key points, and next steps."
    )
    chat_payload = ChatRequest(message=prompt, mode="research", long_answer=True, use_search=payload.use_search)
    return lumora_brain_engine(request, chat_payload, fast=False, force_long=True)


# =============================================================================
# ERROR HANDLING
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = make_request_id()
    log_event(
        "error",
        {
            "error_id": error_id,
            "path": str(request.url.path),
            "error": str(exc),
            "traceback": traceback.format_exc()[-3000:],
        },
    )

    if isinstance(exc, HTTPException):
        raise exc

    return {
        "ok": False,
        "error": "Internal server error.",
        "error_id": error_id,
        "detail": str(exc) if ENVIRONMENT != "production" else "Check server logs for details.",
    }









