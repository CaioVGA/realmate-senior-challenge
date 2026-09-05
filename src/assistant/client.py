from functools import lru_cache

from django.conf import settings
from openai import OpenAI


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_TIMEOUT_SECONDS)
