from typing import Optional
from app.core.config import settings


async def translate(text: str, target_lang: str = "en") -> Optional[str]:
    if not settings.DEEPL_API_KEY:
        return None
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api-free.deepl.com/v2/translate",
                                  data={"auth_key": settings.DEEPL_API_KEY,
                                        "text": text, "target_lang": target_lang.upper()})
            return r.json()["translations"][0]["text"]
    except Exception:
        return None
