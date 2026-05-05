from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import List, Dict, Any, Optional
import os
import re
import base64
from io import BytesIO
import requests


# =============================================================================
# LUMORA BACKEND
# Version: 5.0.0
# Features:
# - Text chat through Hugging Face Router
# - Internet search through Tavily
# - Image generation through Hugging Face InferenceClient
# - Video generation through Hugging Face InferenceClient
# - Date/time handling
# - Study, research, writing, coding, data, image, and video support
# =============================================================================


APP_NAME = "Lumora Backend"
APP_VERSION = "5.0.0"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Advanced FastAPI backend for Lumora with AI chat, internet search, "
        "image generation, video generation, study tools, research support, "
        "coding help, and data help."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Local development only. Restrict this before production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ENVIRONMENT CONFIG
# =============================================================================

HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

HF_MODEL = os.getenv(
    "HF_MODEL",
    "meta-llama/Llama-3.1-8B-Instruct:fastest",
).strip()

HF_IMAGE_MODEL = os.getenv(
    "HF_IMAGE_MODEL",
    "black-forest-labs/FLUX.1-schnell",
).strip()

HF_VIDEO_MODEL = os.getenv(
    "HF_VIDEO_MODEL",
    "Lightricks/LTX-Video-0.9.8-13B-distilled",
).strip()

HF_VIDEO_PROVIDER = os.getenv(
    "HF_VIDEO_PROVIDER",
    "fal-ai",
).strip()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

DEFAULT_MAX_TOKENS = int(os.getenv("LUMORA_MAX_TOKENS", "2600"))
DEFAULT_TEMPERATURE = float(os.getenv("LUMORA_TEMPERATURE", "0.45"))


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    mode: str = "study"
    history: List[Dict[str, Any]] = Field(default_factory=list)


class ImageRequest(BaseModel):
    prompt: str
    style: str = "professional realistic"
    width: int = 1024
    height: int = 1024
    negative_prompt: str = (
        "blurry, low quality, distorted, ugly, bad anatomy, watermark, text artifacts"
    )


class VideoRequest(BaseModel):
    prompt: str
    style: str = "professional educational video"
    seconds: int = 4
    negative_prompt: str = (
        "blurry, low quality, distorted, ugly, watermark, text artifacts, flickering"
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def safe_zone_now(zone_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(zone_name))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone.utc)


def normalize_text(text: str) -> str:
    return (text or "").strip()


def contains_any(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def clamp_dimension(value: int) -> int:
    if value < 256:
        return 256
    if value > 1024:
        return 1024
    return value


def clamp_seconds(value: int) -> int:
    if value < 2:
        return 2
    if value > 8:
        return 8
    return value


def limit_history(
    history: List[Dict[str, Any]],
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    if not history:
        return []

    cleaned_history = []

    for item in history[-max_items:]:
        role = str(item.get("role", "user")).lower().strip()
        content = str(item.get("content", "")).strip()

        if role not in ["user", "assistant"]:
            role = "user"

        if content:
            cleaned_history.append(
                {
                    "role": role,
                    "content": content[:4000],
                }
            )

    return cleaned_history


def bytes_from_video_result(video_result: Any) -> bytes:
    """
    Hugging Face video outputs are commonly returned as raw bytes.
    This helper also handles file-like objects and output objects that expose blob/content.
    """
    if isinstance(video_result, bytes):
        return video_result

    if isinstance(video_result, bytearray):
        return bytes(video_result)

    if hasattr(video_result, "read"):
        data = video_result.read()
        return bytes(data)

    if hasattr(video_result, "blob"):
        return bytes(video_result.blob)

    if hasattr(video_result, "content"):
        return bytes(video_result.content)

    raise TypeError(f"Unsupported video response type: {type(video_result)}")


# =============================================================================
# BASIC ROUTES
# =============================================================================

@app.get("/")
def home():
    return {
        "ok": True,
        "message": "Lumora Backend is running",
        "version": APP_VERSION,
        "docs": "http://127.0.0.1:8000/docs",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": APP_NAME,
        "version": APP_VERSION,
        "hf_token_set": bool(HF_TOKEN),
        "hf_model": HF_MODEL,
        "hf_image_model": HF_IMAGE_MODEL,
        "hf_video_model": HF_VIDEO_MODEL,
        "hf_video_provider": HF_VIDEO_PROVIDER,
        "tavily_key_set": bool(TAVILY_API_KEY),
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": DEFAULT_TEMPERATURE,
        "utc_time": datetime.now(timezone.utc).isoformat(),
        "eastern_time": safe_zone_now("America/New_York").isoformat(),
        "central_time": safe_zone_now("America/Chicago").isoformat(),
    }


@app.get("/image-health")
def image_health():
    return {
        "ok": True,
        "hf_token_set": bool(HF_TOKEN),
        "hf_image_model": HF_IMAGE_MODEL,
        "endpoint": "/image",
        "required_packages": ["huggingface_hub", "pillow"],
    }


@app.get("/video-health")
def video_health():
    return {
        "ok": True,
        "hf_token_set": bool(HF_TOKEN),
        "hf_video_model": HF_VIDEO_MODEL,
        "hf_video_provider": HF_VIDEO_PROVIDER,
        "endpoint": "/video",
        "required_packages": ["huggingface_hub"],
        "note": "Video generation may be slower than image generation and may require provider access.",
    }


# =============================================================================
# INTERNET SEARCH
# =============================================================================

@app.get("/search-test")
def search_test(q: str):
    query = normalize_text(q)

    if not query:
        raise HTTPException(status_code=400, detail="Missing query parameter q")

    if not TAVILY_API_KEY:
        return {
            "ok": False,
            "error": "TAVILY_API_KEY is missing",
        }

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 6,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            json=payload,
            timeout=35,
        )

        if response.status_code >= 400:
            return {
                "ok": False,
                "status": response.status_code,
                "details": response.text,
            }

        return response.json()

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "Internet search timed out",
        }

    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "error": f"Internet search failed: {e}",
        }


def should_search_internet(message: str) -> bool:
    internet_keywords = [
        "search internet",
        "search online",
        "search the web",
        "look up",
        "google",
        "internet",
        "online",
        "latest",
        "current news",
        "recent",
        "news today",
        "today's news",
        "price today",
        "current price",
        "who is the current",
        "what is happening",
        "2026",
        "2027",
        "new update",
        "recent update",
    ]

    return contains_any(message, internet_keywords)


def internet_search(query: str) -> str:
    if not TAVILY_API_KEY:
        return (
            "Internet search is not enabled because TAVILY_API_KEY is missing. "
            "Set TAVILY_API_KEY before starting the backend."
        )

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": 6,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            json=payload,
            timeout=35,
        )

        if response.status_code >= 400:
            return (
                "Internet search failed.\n"
                f"Status: {response.status_code}\n"
                f"Details: {response.text}"
            )

        data = response.json()

        answer = data.get("answer", "")
        results = data.get("results", [])

        web_context = ""

        if answer:
            web_context += f"Search summary:\n{answer}\n\n"

        web_context += "Search results:\n"

        for i, item in enumerate(results, start=1):
            title = item.get("title", "No title")
            url = item.get("url", "")
            content = item.get("content", "")
            score = item.get("score", "")

            web_context += (
                f"{i}. {title}\n"
                f"URL: {url}\n"
                f"Score: {score}\n"
                f"Content: {content}\n\n"
            )

        return web_context.strip()

    except requests.exceptions.Timeout:
        return "Internet search timed out. Please try again."

    except requests.exceptions.RequestException as e:
        return f"Internet search failed: {e}"

    except Exception as e:
        return f"Unexpected internet search error: {e}"


# =============================================================================
# DATE AND TIME HANDLER
# =============================================================================

def current_datetime_reply(message: str) -> Optional[str]:
    lower = message.lower().strip()

    search_words = [
        "latest",
        "news",
        "search",
        "internet",
        "online",
        "recent",
        "current news",
    ]

    if any(word in lower for word in search_words):
        return None

    eastern_time = safe_zone_now("America/New_York")
    central_time = safe_zone_now("America/Chicago")

    eastern_date = eastern_time.strftime("%A, %B %d, %Y")
    eastern_clock = eastern_time.strftime("%I:%M %p")

    central_date = central_time.strftime("%A, %B %d, %Y")
    central_clock = central_time.strftime("%I:%M %p")

    date_keywords = [
        "date",
        "today date",
        "today's date",
        "current date",
        "what date",
        "what is today",
    ]

    time_keywords = [
        "time",
        "current time",
        "what time",
        "what is the time",
        "clock",
    ]

    wants_date = any(keyword in lower for keyword in date_keywords)
    wants_time = any(keyword in lower for keyword in time_keywords)

    if wants_date and not wants_time:
        return (
            f"Today’s date is {eastern_date} Eastern Time.\n\n"
            f"If you are using Central Time, today’s date is {central_date}."
        )

    if wants_time and not wants_date:
        return (
            f"The current time is {eastern_clock} Eastern Time.\n\n"
            f"If you are using Central Time, it is {central_clock}."
        )

    if wants_date and wants_time:
        return (
            f"Current Eastern Time: {eastern_date} at {eastern_clock}.\n\n"
            f"Current Central Time: {central_date} at {central_clock}."
        )

    return None


# =============================================================================
# IMAGE GENERATION
# =============================================================================

def build_image_prompt(prompt: str, style: str) -> str:
    prompt = normalize_text(prompt)
    style = normalize_text(style) or "professional realistic"

    return (
        f"{prompt}. "
        f"Style: {style}. "
        "High quality, detailed, clean composition, sharp focus, professional lighting."
    )


@app.post("/image")
def generate_image(request: ImageRequest):
    if not HF_TOKEN:
        return {
            "ok": False,
            "error": "HF_TOKEN is missing. Set HF_TOKEN before starting the backend.",
        }

    prompt = normalize_text(request.prompt)

    if not prompt:
        return {
            "ok": False,
            "error": "Please provide an image prompt.",
        }

    width = clamp_dimension(request.width)
    height = clamp_dimension(request.height)

    final_prompt = build_image_prompt(
        prompt=prompt,
        style=request.style,
    )

    try:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            return {
                "ok": False,
                "error": (
                    "Missing package: huggingface_hub. "
                    "Install it with: pip install huggingface_hub pillow"
                ),
            }

        client = InferenceClient(token=HF_TOKEN)

        image = client.text_to_image(
            prompt=final_prompt,
            model=HF_IMAGE_MODEL,
            width=width,
            height=height,
            negative_prompt=request.negative_prompt,
        )

        buffer = BytesIO()
        image.save(buffer, format="PNG")

        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "ok": True,
            "model": HF_IMAGE_MODEL,
            "prompt": final_prompt,
            "width": width,
            "height": height,
            "mime_type": "image/png",
            "image_base64": image_base64,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Image generation failed: {e}",
            "model": HF_IMAGE_MODEL,
        }


# =============================================================================
# VIDEO GENERATION
# =============================================================================

def build_video_prompt(prompt: str, style: str, seconds: int) -> str:
    prompt = normalize_text(prompt)
    style = normalize_text(style) or "professional educational video"
    seconds = clamp_seconds(seconds)

    return (
        f"{prompt}. "
        f"Style: {style}. "
        f"Short {seconds}-second video, smooth motion, stable camera, "
        "high quality, clean composition, no unreadable text, no watermark."
    )


@app.post("/video")
def generate_video(request: VideoRequest):
    if not HF_TOKEN:
        return {
            "ok": False,
            "error": "HF_TOKEN is missing. Set HF_TOKEN before starting the backend.",
        }

    prompt = normalize_text(request.prompt)

    if not prompt:
        return {
            "ok": False,
            "error": "Please provide a video prompt.",
        }

    seconds = clamp_seconds(request.seconds)

    final_prompt = build_video_prompt(
        prompt=prompt,
        style=request.style,
        seconds=seconds,
    )

    try:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            return {
                "ok": False,
                "error": (
                    "Missing package: huggingface_hub. "
                    "Install it with: pip install huggingface_hub"
                ),
            }

        client = InferenceClient(
            provider=HF_VIDEO_PROVIDER,
            api_key=HF_TOKEN,
            timeout=300,
        )

        video = client.text_to_video(
            final_prompt,
            model=HF_VIDEO_MODEL,
        )

        video_bytes = bytes_from_video_result(video)
        video_base64 = base64.b64encode(video_bytes).decode("utf-8")

        return {
            "ok": True,
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
            "prompt": final_prompt,
            "seconds": seconds,
            "mime_type": "video/mp4",
            "video_base64": video_base64,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": f"Video generation failed: {e}",
            "model": HF_VIDEO_MODEL,
            "provider": HF_VIDEO_PROVIDER,
        }


# =============================================================================
# TASK DETECTION AND PROMPTS
# =============================================================================

def is_flashcard_request(message: str) -> bool:
    lower = message.lower()
    return "flashcard" in lower or "flash card" in lower


def is_quiz_request(message: str) -> bool:
    lower = message.lower()
    return "quiz" in lower or "questions" in lower or "multiple choice" in lower


def is_study_plan_request(message: str) -> bool:
    lower = message.lower()
    return "study plan" in lower or "study planner" in lower or "day-by-day" in lower


def is_research_request(message: str) -> bool:
    lower = message.lower()
    return (
        "research" in lower
        or "thesis" in lower
        or "academic paper" in lower
        or "outline" in lower
        or "literature review" in lower
    )


def is_code_request(message: str) -> bool:
    lower = message.lower()
    return (
        "code" in lower
        or "python" in lower
        or "sql" in lower
        or "flutter" in lower
        or "dart" in lower
        or "fastapi" in lower
        or "debug" in lower
    )


def is_image_or_video_request(message: str) -> bool:
    lower = message.lower()
    return (
        "generate image" in lower
        or "create image" in lower
        or "make image" in lower
        or "text to image" in lower
        or "image prompt" in lower
        or "generate video" in lower
        or "create video" in lower
        or "make video" in lower
        or "text to video" in lower
        or "video prompt" in lower
        or "draw" in lower
    )


def task_specific_prompt(message: str) -> str:
    if is_flashcard_request(message):
        return """
The user is asking for flashcards.

Flashcard output rules:
1. Return only the flashcards.
2. Do not add an introduction.
3. Do not add closing comments.
4. Do not say "Let's add more" or similar phrases.
5. Do not use Markdown bold symbols like **.
6. Use plain text only.
7. Return exactly the number requested when a number is provided.
8. Use this exact format:

Flashcard 1
Q: question here
A: answer here

Flashcard 2
Q: question here
A: answer here
"""

    if is_quiz_request(message):
        return """
The user is asking for a quiz.

Quiz output rules:
1. Return the quiz clearly.
2. Do not use Markdown bold symbols like **.
3. Include answers and short explanations.
4. Use plain text headings.
5. Do not add unnecessary introduction or closing comments.
6. If educational level is provided, match the quiz to that level.
7. If all levels are requested, divide the quiz into level sections.
"""

    if is_study_plan_request(message):
        return """
The user is asking for a study plan.

Study plan output rules:
1. Make the plan practical and clear.
2. Use day-by-day formatting when appropriate.
3. Include topics, practice tasks, and review tasks.
4. Include checkpoints or mini projects when useful.
5. Do not use Markdown bold symbols like **.
6. Avoid unnecessary introduction.
7. If student name is provided, personalize the plan.
"""

    if is_research_request(message):
        return """
The user is asking for research or academic writing.

Research output rules:
1. Write complete sections and do not stop in the middle of a sentence.
2. Use academic but understandable language.
3. Include thesis statements, outlines, key points, and research questions when requested.
4. For long papers, use clear section headings.
5. Add a conclusion when requested.
6. Do not invent sources.
7. If internet search results are provided, use only those results for current facts.
8. Use clean plain text only.
"""

    if is_code_request(message):
        return """
The user is asking for code or debugging help.

Code output rules:
1. Give complete working code when requested.
2. Explain exact file paths when needed.
3. Avoid unnecessary theory.
4. Mention required packages or commands.
5. Be precise and practical.
"""

    if is_image_or_video_request(message):
        return """
The user may be asking about image or video generation.

Visual generation rules:
1. If the user wants an actual image, tell them Lumora can use the /image endpoint.
2. If the user wants an actual video, tell them Lumora can use the /video endpoint.
3. Help create strong prompts.
4. Keep prompts detailed, visual, and professional.
5. Do not pretend generated media exists inside chat unless the media endpoint is used.
"""

    return """
General output rules:
1. Be clear, direct, and helpful.
2. Do not use excessive Markdown.
3. Avoid raw Markdown symbols like ** unless absolutely necessary.
4. Do not stop in the middle of a sentence.
"""


def system_prompt(mode: str) -> str:
    mode = mode.lower().strip()

    base_prompt = """
You are Lumora.

Identity:
- Your name is Lumora.
- You are an advanced research, study, writing, coding, image-prompting, video-prompting, and data assistant.
- You help learners, students, researchers, professionals, and builders.

Important rules:
1. Be clear, helpful, practical, and accurate.
2. If internet search results are provided, answer only from those results for current information.
3. Do not invent news, dates, companies, funding amounts, source names, citations, or URLs.
4. Include useful source links from the search results when web results are provided.
5. If the search results are weak or not enough, say that clearly.
6. Do not guess current date or time. The backend handles real date/time.
7. Use clean plain text. Avoid Markdown bold symbols like **.
8. For long academic answers, finish the answer completely and do not stop mid-sentence.
9. When the user asks for code, give complete code with the correct file path.
10. When the user asks for image generation, explain that the /image endpoint generates the image.
11. When the user asks for video generation, explain that the /video endpoint generates the video.
"""

    if mode == "study":
        return base_prompt + """
Study mode:
- Explain topics step by step using simple language and examples.
- Help with study plans, quizzes, flashcards, exam prep, and academic learning.
- Adjust explanations to the student's educational level.
"""

    if mode == "research":
        return base_prompt + """
Research mode:
- Help summarize topics, organize ideas, create outlines, generate thesis statements,
  write research drafts, compare sources, and structure academic papers.
- Use professional academic language.
- For research drafts, include complete paragraphs and conclusions when requested.
"""

    if mode == "writing":
        return base_prompt + """
Writing mode:
- Improve grammar, clarity, tone, structure, and professional wording.
- Support emails, essays, reports, resumes, cover letters, and academic writing.
- Preserve the user's intended meaning.
"""

    if mode == "data":
        return base_prompt + """
Data mode:
- Help with Python, SQL, statistics, machine learning, Spark, dashboards,
  Power BI, Tableau, data cleaning, EDA, visualization, and reports.
- Explain code step by step when needed.
- Use practical examples.
"""

    if mode == "image":
        return base_prompt + """
Image mode:
- Help the user create strong image prompts.
- Explain image style, lighting, composition, and visual details clearly.
"""

    if mode == "video":
        return base_prompt + """
Video mode:
- Help the user create short, clear video prompts.
- Include motion, camera direction, subject, scene, and style.
- Avoid asking video models to generate readable text inside the video.
"""

    return base_prompt + """
General mode:
- Answer clearly and professionally.
"""


# =============================================================================
# RESPONSE CLEANER AND FALLBACK
# =============================================================================

def clean_response_text(text: str, original_message: str = "") -> str:
    if not text:
        return text

    cleaned = text.replace("**", "")
    cleaned = cleaned.replace("__", "")

    if is_flashcard_request(original_message):
        remove_patterns = [
            r"(?i)^let'?s add.*$",
            r"(?i)^here are.*flashcards.*$",
            r"(?i)^sure[,!]?.*$",
            r"(?i)^of course[,!]?.*$",
            r"(?i)^i hope.*$",
            r"(?i)^these flashcards.*$",
        ]

        lines = cleaned.splitlines()
        filtered_lines = []

        for line in lines:
            stripped = line.strip()
            should_remove = False

            for pattern in remove_patterns:
                if re.match(pattern, stripped):
                    should_remove = True
                    break

            if not should_remove:
                filtered_lines.append(line)

        cleaned = "\n".join(filtered_lines)

    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned


def fallback_reply(message: str, mode: str) -> str:
    realtime_reply = current_datetime_reply(message)
    if realtime_reply:
        return realtime_reply

    lower = message.lower().strip()

    if lower in ["hello", "hi", "hey"]:
        return (
            "Hello! I’m Lumora. I can help you study, research, write, "
            "create quizzes, make flashcards, search the internet, generate images, generate videos, code, and work on data."
        )

    if "how are you" in lower:
        return (
            "I’m doing great and ready to help you study, research, write, "
            "search online, generate images, generate videos, code, or work on data projects."
        )

    return (
        f"I received your message: {message}\n\n"
        "The local backend is working, but the real AI model is not connected yet. "
        "Set HF_TOKEN before starting the backend."
    )


# =============================================================================
# HUGGING FACE CHAT CALL
# =============================================================================

def call_huggingface(message: str, mode: str, history: List[Dict[str, Any]]) -> str:
    if not HF_TOKEN:
        return fallback_reply(message, mode)

    web_context = ""

    if should_search_internet(message):
        web_context = internet_search(message)

    messages = [
        {
            "role": "system",
            "content": system_prompt(mode),
        },
        {
            "role": "system",
            "content": task_specific_prompt(message),
        },
    ]

    if web_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Internet search results are available below. "
                    "Use only these results for current information. "
                    "Include useful source links from these results.\n\n"
                    f"{web_context}"
                ),
            }
        )

    for item in limit_history(history, max_items=10):
        messages.append(item)

    messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": DEFAULT_MAX_TOKENS,
    }

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            HF_ROUTER_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

    except requests.exceptions.Timeout:
        return (
            "Lumora backend is working, but the AI request timed out. "
            "Please try again with a shorter question or reduce the requested output length."
        )

    except requests.exceptions.RequestException as e:
        return (
            "Lumora backend is working, but it could not reach the AI provider.\n\n"
            f"Error: {e}"
        )

    if response.status_code >= 400:
        return (
            "Lumora connected to the backend, but the AI provider returned an error.\n\n"
            f"Status: {response.status_code}\n"
            f"Details: {response.text}\n\n"
            "Try changing HF_MODEL or checking that your Hugging Face token has access."
        )

    try:
        data = response.json()
        raw_reply = data["choices"][0]["message"]["content"]
        return clean_response_text(raw_reply, message)

    except Exception:
        return (
            "Lumora received a response from the AI provider, but the format was unexpected.\n\n"
            f"Raw response: {response.text}"
        )


@app.post("/chat")
def chat(request: ChatRequest):
    message = request.message.strip()

    if not message:
        return {
            "reply": "Please type a message first.",
        }

    realtime_reply = current_datetime_reply(message)
    if realtime_reply:
        return {
            "reply": realtime_reply,
        }

    reply = call_huggingface(
        message=message,
        mode=request.mode,
        history=request.history,
    )

    reply = clean_response_text(reply, message)

    return {
        "reply": reply,
    }
