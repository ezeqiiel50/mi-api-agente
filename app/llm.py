import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter

load_dotenv()

_limiter = InMemoryRateLimiter(
    requests_per_second=0.15, 
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)

def get_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        max_retries=6,
        rate_limiter=_limiter,
    )

def text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(
        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
    )